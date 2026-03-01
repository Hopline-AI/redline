"""CLI to trigger and manage HF Jobs programmatically."""

from __future__ import annotations

import argparse
import os
import sys
import time

import yaml
from huggingface_hub import HfApi

# Map our YAML gpu_type names to HF Jobs flavor IDs
FLAVOR_MAP = {
    "nvidia-l4": "t4-medium",
    "nvidia-a10g": "a10g-small",
    "nvidia-a100": "a10g-large",
    "cpu": "cpu-basic",
    "cpu-basic": "cpu-basic",
    "cpu-upgrade": "cpu-upgrade",
}


def _load_config(config_path: str) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def _resolve_env(config: dict, overrides: dict[str, str] | None = None) -> dict[str, str]:
    """Resolve ${VAR:-default} references from os.environ."""
    env = {}
    for key, val in config.get("env", {}).items():
        if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
            expr = val[2:-1]
            if ":-" in expr:
                var_name, default = expr.split(":-", 1)
            else:
                var_name, default = expr, ""
            env[key] = os.environ.get(var_name, default)
        else:
            env[key] = str(val)
    if overrides:
        env.update(overrides)
    return env


def _build_command(config: dict) -> str:
    """Combine setup and command blocks into a single shell command."""
    parts = []
    setup = config.get("setup", "").strip()
    command = config.get("command", "").strip()
    if setup:
        parts.append(setup)
    if command:
        parts.append(command)
    return "\n".join(parts)


def _get_flavor(config: dict) -> str:
    compute = config.get("compute", {})
    gpu_type = compute.get("gpu_type", "")
    accelerator = compute.get("accelerator", "cpu")
    if accelerator == "cpu":
        return "cpu-basic"
    return FLAVOR_MAP.get(gpu_type, "t4-medium")


def trigger_job(config_path: str, env_overrides: dict[str, str] | None = None) -> str:
    """Submit an HF Job from a YAML config. Returns the job ID."""
    config = _load_config(config_path)
    env = _resolve_env(config, env_overrides)
    flavor = _get_flavor(config)
    command = _build_command(config)
    image = config.get("image", "python:3.12-slim")

    # Split env into non-secret vars and secrets
    secret_keys = {"HF_TOKEN", "WANDB_API_KEY", "MISTRAL_API_KEY", "GEMINI_API_KEY"}
    secrets = {k: v for k, v in env.items() if k in secret_keys and v}
    plain_env = {k: v for k, v in env.items() if k not in secret_keys}

    print(f"Submitting HF Job: {config['name']}")
    print(f"  Description: {config.get('description', '')}")
    print(f"  Image:       {image}")
    print(f"  Flavor:      {flavor}")
    print(f"  Env vars:    {list(plain_env.keys())}")
    print(f"  Secrets:     {list(secrets.keys())}")

    api = HfApi()
    job = api.run_job(
        image=image,
        command=["bash", "-euxo", "pipefail", "-c", command],
        env=plain_env,
        secrets=secrets,
        flavor=flavor,
    )

    print(f"  Job ID:  {job.id}")
    print(f"  Job URL: {job.url}")
    return job.id


def _print_job_logs(api: HfApi, job_id: str):
    """Fetch and print the last logs from a job."""
    try:
        logs = api.fetch_job_logs(job_id=job_id)
        print(f"  --- Job logs for {job_id} ---")
        for line in logs:
            print(f"  | {line}")
        print(f"  --- End logs ---")
    except Exception as e:
        print(f"  (could not fetch logs: {e})")


def wait_for_job(job_id: str, poll_interval: int = 30) -> str:
    """Poll until job completes. Returns final status stage."""
    api = HfApi()
    print(f"Polling job {job_id}...")
    while True:
        info = api.inspect_job(job_id=job_id)
        stage = info.status.stage
        print(f"  Status: {stage}")
        if stage in ("COMPLETED", "ERROR", "CANCELED"):
            if stage == "ERROR":
                _print_job_logs(api, job_id)
            return stage
        time.sleep(poll_interval)


def check_job_status(job_id: str):
    api = HfApi()
    info = api.inspect_job(job_id=job_id)
    print(f"Job {job_id}: {info.status.stage}")


def run_pipeline(stages: list[str], env_overrides: dict[str, str] | None = None):
    """Run pipeline stages sequentially: each must complete before the next starts."""
    job_configs = {
        "validate": "jobs/validate_data.yaml",
        "retrain": "jobs/retrain.yaml",
        "eval": "jobs/eval.yaml",
        "generate": "jobs/generate_data.yaml",
    }

    for stage in stages:
        if stage not in job_configs:
            print(f"Unknown stage: {stage}. Available: {list(job_configs.keys())}")
            sys.exit(1)

        print(f"\n{'='*50}\nStage: {stage}\n{'='*50}")
        job_id = trigger_job(job_configs[stage], env_overrides)
        status = wait_for_job(job_id)

        if status != "COMPLETED":
            print(f"Stage '{stage}' failed with status: {status}. Aborting pipeline.")
            sys.exit(1)

        print(f"Stage '{stage}' completed successfully.")


def main():
    parser = argparse.ArgumentParser(description="Manage Redline HF Jobs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Trigger a job and wait")
    run_parser.add_argument("config", help="Job YAML config path")
    run_parser.add_argument("--env", nargs="*", help="Environment overrides (KEY=VALUE)")
    run_parser.add_argument("--no-wait", action="store_true", help="Submit and return immediately")

    status_parser = subparsers.add_parser("status", help="Check job status")
    status_parser.add_argument("job_id", help="HF Job ID")

    pipeline_parser = subparsers.add_parser("pipeline", help="Run pipeline stages sequentially")
    pipeline_parser.add_argument(
        "stages",
        nargs="+",
        choices=["validate", "retrain", "eval", "generate"],
    )
    pipeline_parser.add_argument("--env", nargs="*", help="Environment overrides (KEY=VALUE)")

    args = parser.parse_args()

    def parse_env(env_list):
        result = {}
        for item in (env_list or []):
            key, val = item.split("=", 1)
            result[key] = val
        return result

    if args.command == "run":
        overrides = parse_env(args.env)
        job_id = trigger_job(args.config, overrides)
        if not args.no_wait:
            status = wait_for_job(job_id)
            if status != "COMPLETED":
                sys.exit(1)

    elif args.command == "status":
        check_job_status(args.job_id)

    elif args.command == "pipeline":
        overrides = parse_env(args.env)
        run_pipeline(args.stages, overrides)


if __name__ == "__main__":
    main()
