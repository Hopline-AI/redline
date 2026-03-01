"""Auto-retrain pipeline: lawyer corrections accumulate, then trigger HF Jobs."""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi

log = logging.getLogger(__name__)

CORRECTIONS_PATH = Path("data/lawyer_corrections.jsonl")
TRAIN_PATH = Path("data/train.jsonl")
ARCHIVE_DIR = Path("data/lawyer_corrections_archive")

RETRAIN_THRESHOLD = int(os.environ.get("RETRAIN_THRESHOLD", "10"))
HF_DATASET_REPO = os.environ.get("HF_DATASET_REPO", "khushiyant/redline-compliance-extraction")

HF_MODEL_REPO = os.environ.get("HF_MODEL_REPO", "mistral-hackaton-2026/redline-extractor")

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
    try:
        api.create_repo(
            repo_id=HF_DATASET_REPO,
            repo_type="dataset",
            exist_ok=True,
        )
    except Exception as e:
        log.warning("create_repo failed (repo may already exist): %s", e)
    api.upload_file(
        path_or_fileobj=str(TRAIN_PATH),
        path_in_repo="train.jsonl",
        repo_id=HF_DATASET_REPO,
        repo_type="dataset",
        commit_message="Auto-retrain: merge lawyer corrections into training data",
    )


def trigger_hf_pipeline():
    """Submit validate -> retrain -> eval jobs via run_job.py, waiting for each."""
    import subprocess
    import sys

    env = {
        **os.environ,
        "HF_DATASET_REPO": HF_DATASET_REPO,
        "HF_MODEL_REPO": HF_MODEL_REPO,
        "WANDB_PROJECT": "redline-compliance",
    }

    log.info("Submitting HF Jobs pipeline: validate -> retrain -> eval")
    result = subprocess.run(
        [sys.executable, "jobs/run_job.py", "pipeline", "validate", "retrain", "eval"],
        env=env,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        log.info("Pipeline output:\n%s", result.stdout)
    if result.returncode != 0:
        log.error("Pipeline failed:\n%s", result.stderr)
        raise RuntimeError(f"HF Jobs pipeline failed: {result.stderr}")


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
