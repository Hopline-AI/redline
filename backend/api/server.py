"""FastAPI backend for the Redline compliance engine.

Exposes extraction + comparison pipeline to the frontend.
Traces every extraction via W&B Weave.
Lawyer edits are converted to training samples and logged as W&B Artifacts.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.auto_retrain import (
    check_and_trigger,
    get_status as get_retrain_status,
    initialize_from_disk,
)
from api.models import (
    ComparisonResult,
    ComplianceReportResponse,
    ExtractionResult,
    JobStatus,
    RetrainStatus,
    ReviewRequest,
    ReviewResponse,
    UploadResponse,
)
from engine.comparator import compare_all
from engine.pdf_parser import chunk_by_sections, parse_pdf
from engine.report import generate_report, report_to_dict

app = FastAPI(
    title="Redline Compliance Engine",
    description="Explainable compliance engine for HR policy verification",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (hackathon scope)
jobs: dict[str, dict] = {}

LAWYER_EDITS_DIR = Path("data/lawyer_edits")
LAWYER_EDITS_DIR.mkdir(parents=True, exist_ok=True)
LAWYER_CORRECTIONS_PATH = Path("data/lawyer_corrections.jsonl")

MODEL_ENDPOINT = os.environ.get("REDLINE_MODEL_ENDPOINT", "http://localhost:8080")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
USE_MISTRAL_API = os.environ.get("REDLINE_USE_MISTRAL_API", "false").lower() == "true"

SYSTEM_MESSAGE = (
    "You are a compliance extraction engine. Your task is to extract all decision "
    "rules from company policy documents into structured JSON. Output only valid JSON "
    "matching the provided schema. Do not interpret, evaluate, or offer opinions on "
    "the rules — only extract them exactly as stated in the policy text."
)

USER_TEMPLATE = (
    "Extract all decision rules from the following company policy into structured JSON. "
    "For each rule, identify the rule type, conditions, actions, and include the exact "
    "source text from the policy.\n\nPolicy text:\n{policy_text}"
)

_weave_initialized = False


def _init_weave():
    global _weave_initialized
    if _weave_initialized:
        return True
    try:
        import weave
        weave.init("redline-compliance")
        _weave_initialized = True
        return True
    except Exception:
        return False


def _parse_prompt_template(policy_text: str) -> tuple[str, str]:
    template = Path("schema/prompt_template.txt").read_text()
    system_msg = template.split("USER:")[0].replace("SYSTEM:", "").strip()
    user_msg = template.split("USER:")[1].strip().replace("{policy_text}", policy_text)
    return system_msg, user_msg


def _get_model_name() -> str:
    """Auto-detect model name from vLLM endpoint."""
    try:
        resp = requests.get(f"{MODEL_ENDPOINT}/v1/models", timeout=5)
        return resp.json()["data"][0]["id"]
    except Exception:
        return "redline-extractor"


def _extract_with_endpoint(policy_text: str) -> dict:
    """Call the vLLM/TGI endpoint for extraction."""
    system_msg, user_msg = _parse_prompt_template(policy_text)
    model_name = _get_model_name()

    start = time.time()
    resp = requests.post(
        f"{MODEL_ENDPOINT}/v1/chat/completions",
        json={
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.0,
            "max_tokens": 2048,
        },
        timeout=120,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    latency_ms = (time.time() - start) * 1000

    if _weave_initialized:
        try:
            import weave
            weave.publish({
                "input_policy_text": policy_text[:500],
                "raw_model_output": content[:500],
                "latency_ms": latency_ms,
                "model": model_name,
                "inference_mode": "vllm_endpoint",
            }, name=f"extraction_{int(time.time())}")
        except Exception:
            pass

    return json.loads(content)


def _extract_with_mistral(policy_text: str) -> dict:
    """Call Mistral API for extraction."""
    from mistralai import Mistral

    client = Mistral(api_key=MISTRAL_API_KEY)
    system_msg, user_msg = _parse_prompt_template(policy_text)

    start = time.time()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    latency_ms = (time.time() - start) * 1000

    if _weave_initialized:
        try:
            import weave
            weave.publish({
                "input_policy_text": policy_text[:500],
                "raw_model_output": content[:500],
                "latency_ms": latency_ms,
                "model": "mistral-small-latest",
                "inference_mode": "mistral_api",
            }, name=f"extraction_{int(time.time())}")
        except Exception:
            pass

    return json.loads(content)


def _run_pipeline(job_id: str, text: str, policy_name: str):
    """Background pipeline: parse -> chunk -> extract -> compare -> store."""
    job = jobs[job_id]

    try:
        job["status"] = JobStatus.extracting
        chunks = chunk_by_sections(text)

        all_rules = []
        metadata = None
        for chunk in chunks:
            try:
                if USE_MISTRAL_API:
                    result = _extract_with_mistral(chunk)
                else:
                    result = _extract_with_endpoint(chunk)
                all_rules.extend(result.get("rules", []))
                if metadata is None and "metadata" in result:
                    metadata = result["metadata"]
            except Exception as e:
                job.setdefault("errors", []).append(f"Extraction error: {e}")

        if metadata is None:
            metadata = {
                "policy_name": policy_name,
                "effective_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "applicable_jurisdictions": ["CA", "federal"],
            }

        job["extraction"] = {"rules": all_rules, "metadata": metadata}

        job["status"] = JobStatus.comparing
        comparison = compare_all(all_rules)
        job["comparison"] = comparison

        report = generate_report(policy_name, all_rules, report_id=f"report_{job_id}")
        job["report"] = report_to_dict(report)

        job["status"] = JobStatus.complete

    except Exception as e:
        job["status"] = JobStatus.error
        job["error"] = str(e)


def _build_training_sample(policy_text: str, corrected_extraction: dict) -> dict:
    """Convert a lawyer-corrected extraction into a Mistral training format sample."""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": USER_TEMPLATE.format(policy_text=policy_text)},
            {"role": "assistant", "content": json.dumps(corrected_extraction, indent=2)},
        ]
    }


def _save_correction_and_log(job_id: str, policy_text: str, corrected_rules: list[dict], metadata: dict):
    """Save lawyer-corrected sample to disk and log as W&B Artifact."""
    corrected_extraction = {"rules": corrected_rules, "metadata": metadata}
    sample = _build_training_sample(policy_text, corrected_extraction)

    with open(LAWYER_CORRECTIONS_PATH, "a") as f:
        f.write(json.dumps(sample) + "\n")

    correction_count = sum(1 for _ in open(LAWYER_CORRECTIONS_PATH))

    try:
        import wandb

        if wandb.run is None:
            wandb.init(
                project="redline-compliance",
                name=f"lawyer-correction-{job_id}",
                config={"phase": "lawyer_feedback", "job_id": job_id},
            )

        artifact = wandb.Artifact(
            name="lawyer-corrections",
            type="dataset",
            description=f"Lawyer-corrected training samples ({correction_count} total)",
            metadata={"correction_count": correction_count, "last_job_id": job_id},
        )
        artifact.add_file(str(LAWYER_CORRECTIONS_PATH))
        wandb.log_artifact(artifact)
        wandb.log({"lawyer/total_corrections": correction_count})
        wandb.finish()
    except Exception as e:
        print(f"W&B artifact logging failed: {e}")


@app.on_event("startup")
async def startup():
    _init_weave()
    initialize_from_disk()


@app.post("/upload", response_model=UploadResponse)
async def upload_policy(
    background_tasks: BackgroundTasks,
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    policy_name: str = Form("Uploaded Policy"),
):
    """Upload a policy document (PDF or text) for extraction."""
    if file is None and text is None:
        raise HTTPException(status_code=400, detail="Provide either a file or text")

    job_id = str(uuid.uuid4())[:8]

    if file is not None:
        content = await file.read()
        if file.filename and file.filename.endswith(".pdf"):
            tmp_path = Path(f"/tmp/redline_{job_id}.pdf")
            tmp_path.write_bytes(content)
            plain_text = parse_pdf(tmp_path)
            tmp_path.unlink(missing_ok=True)
        else:
            plain_text = content.decode("utf-8")
        if not policy_name or policy_name == "Uploaded Policy":
            policy_name = file.filename or "Uploaded Policy"
    else:
        plain_text = text

    jobs[job_id] = {
        "job_id": job_id,
        "status": JobStatus.parsing,
        "policy_name": policy_name,
        "raw_text": plain_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    background_tasks.add_task(_run_pipeline, job_id, plain_text, policy_name)

    return UploadResponse(job_id=job_id, status=JobStatus.pending)


@app.get("/extract/{job_id}", response_model=ExtractionResult)
async def get_extraction(job_id: str):
    """Get extracted rules for a job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    extraction = job.get("extraction", {})

    return ExtractionResult(
        job_id=job_id,
        status=job["status"],
        rules=extraction.get("rules", []),
        metadata=extraction.get("metadata"),
    )


@app.get("/compare/{job_id}", response_model=ComparisonResult)
async def get_comparison(job_id: str):
    """Get compliance comparison results."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    comparison = job.get("comparison", {})

    return ComparisonResult(
        job_id=job_id,
        status=job["status"],
        comparisons=comparison.get("comparisons", []),
        missing_requirements=comparison.get("missing_requirements", []),
        summary=comparison.get("summary", {}),
    )


@app.post("/review/{job_id}", response_model=ReviewResponse)
async def submit_review(job_id: str, request: ReviewRequest, background_tasks: BackgroundTasks):
    """Submit lawyer reviews. Edits become retraining samples logged to W&B."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    extraction = job.get("extraction", {})

    report = job.get("report", {})
    rule_results = report.get("rule_results", [])
    rule_map = {r["policy_rule_id"]: r for r in rule_results}

    has_edits = False
    corrected_rules = list(extraction.get("rules", []))

    for review in request.reviews:
        if review.rule_id in rule_map:
            rule_map[review.rule_id]["lawyer_status"] = review.action.value
            rule_map[review.rule_id]["lawyer_notes"] = review.notes

        if review.action.value == "edit" and review.edited_rule:
            has_edits = True
            for i, rule in enumerate(corrected_rules):
                if rule.get("rule_id") == review.rule_id:
                    corrected_rules[i] = review.edited_rule.model_dump()
                    break

        if review.action.value == "deny":
            has_edits = True
            corrected_rules = [r for r in corrected_rules if r.get("rule_id") != review.rule_id]

    edits_path = LAWYER_EDITS_DIR / f"{job_id}.jsonl"
    with open(edits_path, "a") as f:
        for review in request.reviews:
            edit_record = {
                "job_id": job_id,
                "rule_id": review.rule_id,
                "action": review.action.value,
                "notes": review.notes,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            if review.edited_rule:
                edit_record["edited_rule"] = review.edited_rule.model_dump()
            f.write(json.dumps(edit_record) + "\n")

    retrain_triggered = False
    if has_edits:
        policy_text = job.get("raw_text", "")
        metadata = extraction.get("metadata", {})
        _save_correction_and_log(job_id, policy_text, corrected_rules, metadata)
        retrain_triggered = check_and_trigger(background_tasks)

    msg = f"Saved {len(request.reviews)} reviews."
    if has_edits:
        msg += " Corrections logged to W&B for retraining."
    if retrain_triggered:
        msg += " Auto-retrain triggered."

    return ReviewResponse(
        job_id=job_id,
        reviewed_count=len(request.reviews),
        message=msg,
    )


@app.get("/report/{job_id}", response_model=ComplianceReportResponse)
async def get_report(job_id: str):
    """Get the final compliance report."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    report = job.get("report")

    if report is None:
        raise HTTPException(status_code=409, detail="Report not yet generated")

    return ComplianceReportResponse(
        report_id=report["report_id"],
        job_id=job_id,
        policy_name=report["policy_name"],
        generated_at=report["generated_at"],
        rule_results=report["rule_results"],
        missing_requirements=report["missing_requirements"],
        summary=report["summary"],
    )


@app.get("/retrain/status", response_model=RetrainStatus)
async def retrain_status():
    """Show auto-retrain pipeline status."""
    return RetrainStatus(**get_retrain_status())


@app.get("/health")
async def health():
    corrections = 0
    if LAWYER_CORRECTIONS_PATH.exists():
        corrections = sum(1 for _ in open(LAWYER_CORRECTIONS_PATH))
    return {
        "status": "ok",
        "jobs_count": len(jobs),
        "lawyer_corrections": corrections,
        "weave_enabled": _weave_initialized,
    }
