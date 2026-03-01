"""Auto-retrain pipeline: lawyer corrections accumulate, then trigger HF Jobs."""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi, inspect_job, run_uv_job

log = logging.getLogger(__name__)

CORRECTIONS_PATH = Path("data/lawyer_corrections.jsonl")
TRAIN_PATH = Path("data/train.jsonl")
ARCHIVE_DIR = Path("data/lawyer_corrections_archive")

RETRAIN_THRESHOLD = int(os.environ.get("RETRAIN_THRESHOLD", "10"))
HF_DATASET_REPO = os.environ.get("HF_DATASET_REPO", "khushiyant/redline-compliance-extraction")

PIPELINE_JOBS = [
    {
        "name": "validate",
        "script": "data/validate_data.py",
        "script_args": ["data/train.jsonl", "--schema", "schema/decision_logic.json"],
        "dependencies": ["jsonschema"],
        "flavor": "cpu-basic",
        "timeout": "10m",
    },
    {
        "name": "retrain",
        "script": "training/finetune.py",
        "script_args": ["--config", "training/config.yaml"],
        "dependencies": [
            "unsloth", "transformers", "trl", "peft",
            "bitsandbytes", "wandb", "datasets", "accelerate", "pyyaml",
        ],
        "flavor": "a10g-large",
        "timeout": "2h",
    },
    {
        "name": "eval",
        "script": "eval/finetuned_eval.py",
        "script_args": ["--test-data", "data/test.jsonl", "--model", "mistral-small-latest"],
        "dependencies": ["mistralai", "wandb", "weave", "jsonschema"],
        "flavor": "cpu-upgrade",
        "timeout": "30m",
    },
]

# State tracked across the server's lifetime
_corrections_since_retrain = 0
_total_corrections = 0
_last_retrain_at: str | None = None
_last_retrain_error: str | None = None
_retrain_in_progress = False
_lock = threading.Lock()


def initialize_from_disk():
    """Restore correction counter from disk on server startup."""
    global _corrections_since_retrain, _total_corrections
    if CORRECTIONS_PATH.exists():
        with open(CORRECTIONS_PATH) as f:
            count = sum(1 for _ in f)
        with _lock:
            _corrections_since_retrain = count
            _total_corrections = count


def get_status() -> dict:
    with _lock:
        return {
            "corrections_since_last_retrain": _corrections_since_retrain,
            "total_corrections": _total_corrections,
            "retrain_threshold": RETRAIN_THRESHOLD,
            "last_retrain_at": _last_retrain_at,
            "last_retrain_error": _last_retrain_error,
            "retrain_in_progress": _retrain_in_progress,
        }


def increment_correction_counter():
    global _corrections_since_retrain, _total_corrections
    with _lock:
        _corrections_since_retrain += 1
        _total_corrections += 1


def merge_corrections_into_training() -> tuple[int, list[str]]:
    """Read corrections, validate JSON, append to train.jsonl.

    Returns (merged_count, raw_lines). Does NOT archive — caller archives
    after push/trigger succeed.
    """
    if not CORRECTIONS_PATH.exists():
        return 0, []

    raw_lines = CORRECTIONS_PATH.read_text().strip().splitlines()
    if not raw_lines:
        return 0, []

    valid_lines = []
    for line in raw_lines:
        stripped = line.rstrip()
        if not stripped:
            continue
        try:
            json.loads(stripped)
            valid_lines.append(stripped)
        except json.JSONDecodeError:
            log.warning("Skipping malformed correction line: %s", stripped[:100])

    if not valid_lines:
        return 0, []

    with open(TRAIN_PATH, "a") as f:
        for line in valid_lines:
            f.write(line + "\n")

    return len(valid_lines), raw_lines


def archive_corrections():
    """Move processed corrections file to archive. Call only after push/trigger succeed."""
    if not CORRECTIONS_PATH.exists():
        return
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = ARCHIVE_DIR / f"corrections_{ts}.jsonl"
    shutil.move(str(CORRECTIONS_PATH), str(archive_path))


def push_dataset_to_hub():
    """Upload the updated train.jsonl to HF Hub."""
    token = os.environ.get("HF_TOKEN")
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=str(TRAIN_PATH),
        path_in_repo="train.jsonl",
        repo_id=HF_DATASET_REPO,
        repo_type="dataset",
        commit_message="Auto-retrain: merge lawyer corrections into training data",
    )


def trigger_hf_pipeline():
    """Submit validate -> retrain -> eval jobs via HF Jobs SDK, waiting for each."""
    secrets = {}
    for key in ("HF_TOKEN", "WANDB_API_KEY", "MISTRAL_API_KEY"):
        val = os.environ.get(key)
        if val:
            secrets[key] = val

    for job_config in PIPELINE_JOBS:
        log.info("Submitting HF Job: %s", job_config["name"])
        job = run_uv_job(
            job_config["script"],
            script_args=job_config.get("script_args", []),
            dependencies=job_config.get("dependencies", []),
            flavor=job_config.get("flavor", "cpu-basic"),
            timeout=job_config.get("timeout", "1h"),
            env={"WANDB_PROJECT": "redline-compliance", "HF_DATASET_REPO": HF_DATASET_REPO},
            secrets=secrets,
        )
        log.info("Job submitted: %s (id=%s)", job_config["name"], job.id)

        while True:
            info = inspect_job(job_id=job.id)
            stage = info.status.stage
            if stage in ("COMPLETED", "ERROR", "CANCELED", "DELETED"):
                log.info("Job %s finished: %s", job_config["name"], stage)
                if stage != "COMPLETED":
                    raise RuntimeError(f"HF Job '{job_config['name']}' ended with: {stage}")
                break
            time.sleep(30)


def _log_retrain_event(merged_count: int):
    try:
        import wandb

        wandb.init(
            project="redline-compliance",
            name=f"auto-retrain-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
            config={
                "phase": "auto_retrain",
                "merged_corrections": merged_count,
                "threshold": RETRAIN_THRESHOLD,
            },
        )
        wandb.log({
            "auto_retrain/merged_corrections": merged_count,
            "auto_retrain/threshold": RETRAIN_THRESHOLD,
        })
        wandb.finish()
    except Exception as e:
        log.warning("W&B auto-retrain logging failed: %s", e)


def run_auto_retrain():
    """Called as a background task. _retrain_in_progress is already True (set by check_and_trigger)."""
    global _retrain_in_progress, _corrections_since_retrain, _last_retrain_at, _last_retrain_error

    try:
        merged, _ = merge_corrections_into_training()
        if merged == 0:
            return

        push_dataset_to_hub()
        trigger_hf_pipeline()

        # Archive only after push+trigger succeed
        archive_corrections()
        _log_retrain_event(merged)

        with _lock:
            _corrections_since_retrain = 0
            _last_retrain_at = datetime.now(timezone.utc).isoformat()
            _last_retrain_error = None
    except Exception as e:
        log.exception("Auto-retrain failed")
        with _lock:
            _last_retrain_error = str(e)
    finally:
        with _lock:
            _retrain_in_progress = False


def check_and_trigger(background_tasks) -> bool:
    """Returns True if threshold was met and a retrain was scheduled."""
    increment_correction_counter()

    with _lock:
        should_trigger = (
            _corrections_since_retrain >= RETRAIN_THRESHOLD
            and not _retrain_in_progress
        )
        if should_trigger:
            _retrain_in_progress = True

    if should_trigger:
        background_tasks.add_task(run_auto_retrain)
        return True
    return False
