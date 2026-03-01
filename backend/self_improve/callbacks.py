"""Callbacks that connect the self-improvement loop to HF Jobs + W&B.

retrain_callback: push updated dataset to HF Hub, then trigger
    validate -> retrain -> eval pipeline via HF Jobs SDK.

eval_callback: fetch the latest finished eval run from W&B and
    return a MetricsSnapshot.
"""

from __future__ import annotations

import logging
import os
import time

from huggingface_hub import HfApi, inspect_job

from self_improve.config import TRAIN_JSONL, WANDB_ENTITY, WANDB_PROJECT
from self_improve.inspect_metrics import MetricsSnapshot, fetch_latest_run

log = logging.getLogger(__name__)

HF_DATASET_REPO = os.environ.get(
    "HF_DATASET_REPO", "mistral-hackaton-2026/redline-compliance-extraction"
)
HF_MODEL_REPO = os.environ.get(
    "HF_MODEL_REPO", "mistral-hackaton-2026/redline-extractor"
)

# Jobs config for HF Jobs YAML-based submission (via run_job.py)
JOB_YAMLS = {
    "validate": "jobs/validate_data.yaml",
    "retrain": "jobs/retrain.yaml",
    "eval": "jobs/eval.yaml",
}

# Programmatic pipeline via run_uv_job — each entry is a self-contained script
# that accepts env vars instead of importing local modules.
# For jobs needing the full codebase, use run_job.py with the YAML configs instead.
PIPELINE_STAGES = ["validate", "retrain", "eval"]


def push_dataset_to_hub():
    """Upload train.jsonl to HF Hub so HF Jobs can pick it up."""
    token = os.environ.get("HF_TOKEN")
    api = HfApi(token=token)
    api.upload_file(
        path_or_fileobj=TRAIN_JSONL,
        path_in_repo="train.jsonl",
        repo_id=HF_DATASET_REPO,
        repo_type="dataset",
        commit_message="Self-improvement loop: updated training data",
    )
    log.info("Dataset pushed to %s", HF_DATASET_REPO)


def _submit_and_wait(stage: str) -> str:
    """Submit an HF Job from YAML config and poll until completion."""
    import subprocess
    import yaml

    yaml_path = JOB_YAMLS[stage]
    with open(yaml_path) as f:
        config = yaml.safe_load(f)

    env = {
        **os.environ,
        "HF_DATASET_REPO": HF_DATASET_REPO,
        "HF_MODEL_REPO": HF_MODEL_REPO,
        "WANDB_ENTITY": WANDB_ENTITY or "",
        "WANDB_PROJECT": WANDB_PROJECT,
    }

    log.info("Submitting HF Job: %s (config=%s)", stage, yaml_path)

    # Use huggingface-cli to submit the YAML-defined job
    result = subprocess.run(
        ["huggingface-cli", "jobs", "submit", yaml_path],
        env=env,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        log.error("Job submission failed:\n%s", result.stderr)
        raise RuntimeError(f"HF Job '{stage}' submission failed: {result.stderr}")

    log.info("Job submitted: %s\n%s", stage, result.stdout)

    # Extract job ID from CLI output (format: "Job ID: <id>")
    job_id = None
    for line in result.stdout.splitlines():
        if "job" in line.lower() and ("id" in line.lower() or "url" in line.lower()):
            parts = line.split()
            if parts:
                job_id = parts[-1].strip()
            break

    if not job_id:
        log.warning("Could not parse job ID from output. Cannot poll status.")
        return "SUBMITTED"

    # Poll until done
    while True:
        info = inspect_job(job_id=job_id)
        stage_status = info.status.stage
        log.info("Job %s status: %s", stage, stage_status)
        if stage_status in ("COMPLETED", "ERROR", "CANCELED"):
            if stage_status != "COMPLETED":
                raise RuntimeError(f"HF Job '{stage}' ended with status: {stage_status}")
            return stage_status
        time.sleep(30)


def retrain_callback():
    """Push dataset to HF Hub and run validate -> retrain -> eval pipeline."""
    push_dataset_to_hub()
    for stage in PIPELINE_STAGES:
        _submit_and_wait(stage)
    log.info("Full pipeline completed: validate -> retrain -> eval")


def eval_callback() -> MetricsSnapshot:
    """Fetch the latest finished eval run from W&B."""
    return fetch_latest_run(
        project=WANDB_PROJECT,
        entity=WANDB_ENTITY,
    )
