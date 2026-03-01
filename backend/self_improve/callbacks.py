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

from huggingface_hub import HfApi, inspect_job, run_uv_job

from self_improve.config import TRAIN_JSONL, WANDB_ENTITY, WANDB_PROJECT
from self_improve.inspect_metrics import MetricsSnapshot, fetch_latest_run

log = logging.getLogger(__name__)

HF_DATASET_REPO = os.environ.get(
    "HF_DATASET_REPO", "mistral-hackathon-2026/redline-compliance-extraction"
)
HF_MODEL_REPO = os.environ.get(
    "HF_MODEL_REPO", "mistral-hackathon-2026/redline-compliance-extractor"
)

# Jobs run sequentially: validate → retrain → eval
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


def _submit_and_wait(job_config: dict) -> str:
    """Submit an HF Job and poll until completion. Returns final status."""
    secrets = {}
    for key in ("HF_TOKEN", "WANDB_API_KEY", "MISTRAL_API_KEY", "GEMINI_API_KEY"):
        val = os.environ.get(key)
        if val:
            secrets[key] = val

    log.info("Submitting HF Job: %s", job_config["name"])
    job = run_uv_job(
        job_config["script"],
        script_args=job_config.get("script_args", []),
        dependencies=job_config.get("dependencies", []),
        flavor=job_config.get("flavor", "cpu-basic"),
        timeout=job_config.get("timeout", "1h"),
        env={
            "WANDB_ENTITY": WANDB_ENTITY or "",
            "WANDB_PROJECT": WANDB_PROJECT,
            "HF_DATASET_REPO": HF_DATASET_REPO,
            "HF_MODEL_REPO": HF_MODEL_REPO,
        },
        secrets=secrets,
    )
    log.info("Job submitted: %s (id=%s, url=%s)", job_config["name"], job.id, job.url)

    # Poll until done
    while True:
        info = inspect_job(job_id=job.id)
        stage = info.status.stage
        if stage in ("COMPLETED", "ERROR", "CANCELED"):
            log.info("Job %s finished: %s", job_config["name"], stage)
            if stage != "COMPLETED":
                raise RuntimeError(f"HF Job '{job_config['name']}' ended with status: {stage}")
            return stage
        time.sleep(30)


def retrain_callback():
    """Push dataset to HF Hub and run validate -> retrain -> eval pipeline."""
    push_dataset_to_hub()
    for job_config in PIPELINE_JOBS:
        _submit_and_wait(job_config)
    log.info("Full pipeline completed: validate -> retrain -> eval")


def eval_callback() -> MetricsSnapshot:
    """Fetch the latest finished eval run from W&B."""
    return fetch_latest_run(
        project=WANDB_PROJECT,
        entity=WANDB_ENTITY,
    )
