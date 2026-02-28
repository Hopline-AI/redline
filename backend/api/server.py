"""FastAPI backend for the Redline compliance engine.

Exposes extraction + comparison pipeline to the frontend.
Uses in-memory job store for hackathon scope.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.models import (
    ComparisonResult,
    ComplianceReportResponse,
    ExtractionResult,
    JobStatus,
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

# Model endpoint config
MODEL_ENDPOINT = os.environ.get("REDLINE_MODEL_ENDPOINT", "http://localhost:8080")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
USE_MISTRAL_API = os.environ.get("REDLINE_USE_MISTRAL_API", "false").lower() == "true"


def _extract_with_endpoint(policy_text: str) -> dict:
    """Call the vLLM/TGI endpoint for extraction."""
    import requests

    template_path = Path("schema/prompt_template.txt")
    template = template_path.read_text()
    system_msg = template.split("USER:")[0].replace("SYSTEM:", "").strip()
    user_msg = template.split("USER:")[1].strip().replace("{policy_text}", policy_text)

    resp = requests.post(
        f"{MODEL_ENDPOINT}/v1/chat/completions",
        json={
            "model": "redline-extractor",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.0,
            "max_tokens": 4096,
        },
        timeout=120,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def _extract_with_mistral(policy_text: str) -> dict:
    """Call Mistral API for extraction."""
    from mistralai import Mistral

    client = Mistral(api_key=MISTRAL_API_KEY)
    template_path = Path("schema/prompt_template.txt")
    template = template_path.read_text()
    system_msg = template.split("USER:")[0].replace("SYSTEM:", "").strip()
    user_msg = template.split("USER:")[1].strip().replace("{policy_text}", policy_text)

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def _run_pipeline(job_id: str, text: str, policy_name: str):
    """Background pipeline: parse -> chunk -> extract -> compare -> store."""
    job = jobs[job_id]

    try:
        # Chunk
        job["status"] = JobStatus.extracting
        chunks = chunk_by_sections(text)

        # Extract rules from each chunk
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

        # Compare
        job["status"] = JobStatus.comparing
        comparison = compare_all(all_rules)
        job["comparison"] = comparison

        # Generate report
        report = generate_report(policy_name, all_rules, report_id=f"report_{job_id}")
        job["report"] = report_to_dict(report)

        job["status"] = JobStatus.complete

    except Exception as e:
        job["status"] = JobStatus.error
        job["error"] = str(e)


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
            # Save temp file and parse PDF
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
async def submit_review(job_id: str, request: ReviewRequest):
    """Submit lawyer reviews (approve/deny/edit) for extracted rules."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Apply reviews to report
    report = job.get("report", {})
    rule_results = report.get("rule_results", [])
    rule_map = {r["policy_rule_id"]: r for r in rule_results}

    for review in request.reviews:
        if review.rule_id in rule_map:
            rule_map[review.rule_id]["lawyer_status"] = review.action.value
            rule_map[review.rule_id]["lawyer_notes"] = review.notes

    # Save edits for retraining
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

    return ReviewResponse(
        job_id=job_id,
        reviewed_count=len(request.reviews),
        message=f"Saved {len(request.reviews)} reviews. Edits stored for retraining.",
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


@app.get("/health")
async def health():
    return {"status": "ok", "jobs_count": len(jobs)}
