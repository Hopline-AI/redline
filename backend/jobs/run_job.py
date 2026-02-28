"""CLI to trigger and manage HF Jobs programmatically."""

from __future__ import annotations

import argparse
import os
import sys
import time

from huggingface_hub import HfApi


def trigger_job(api: HfApi, config_path: str, env_overrides: dict[str, str] | None = None):
    """Trigger an HF Job from a YAML config."""
    import yaml

    with open(config_path) as f:
        config = yaml.safe_load(f)

    print(f"Triggering job: {config['name']}")
    print(f"  Description: {config['description']}")
    print(f"  Compute: {config['compute']}")

    # Build environment with overrides
    env = {}
    for key, val in config.get("env", {}).items():
        # Resolve ${VAR} references from os.environ
        if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
            var_expr = val[2:-1]
            if ":-" in var_expr:
                var_name, default = var_expr.split(":-", 1)
            else:
                var_name, default = var_expr, ""
            env[key] = os.environ.get(var_name, default)
        else:
            env[key] = str(val)

    if env_overrides:
        env.update(env_overrides)

    # Use HF Spaces/Jobs API
    # Note: HF Jobs API is evolving; this uses the current pattern
    print(f"\nJob config validated. To submit to HF Jobs:")
    print(f"  huggingface-cli jobs run {config_path}")
    print(f"\nEnvironment variables needed:")
    for key in env:
        val = env[key]
        masked = val[:4] + "..." if len(val) > 8 else val
        print(f"  {key}={masked}")

    return config


def check_job_status(api: HfApi, job_id: str):
    """Check the status of a running HF Job."""
    print(f"Checking job status: {job_id}")
    # HF Jobs status API
    print("  (Use HF dashboard or CLI: huggingface-cli jobs status {job_id})")


def run_pipeline(api: HfApi, stages: list[str]):
    """Run the full pipeline: validate -> retrain -> eval."""
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

        print(f"\n{'='*50}")
        print(f"Stage: {stage}")
        print(f"{'='*50}")
        trigger_job(api, job_configs[stage])
        print()


def main():
    parser = argparse.ArgumentParser(description="Manage Redline HF Jobs")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Trigger a single job
    run_parser = subparsers.add_parser("run", help="Trigger a job")
    run_parser.add_argument("config", help="Job YAML config path")
    run_parser.add_argument("--env", nargs="*", help="Environment overrides (KEY=VALUE)")

    # Check status
    status_parser = subparsers.add_parser("status", help="Check job status")
    status_parser.add_argument("job_id", help="HF Job ID")

    # Run full pipeline
    pipeline_parser = subparsers.add_parser("pipeline", help="Run pipeline stages")
    pipeline_parser.add_argument(
        "stages",
        nargs="+",
        choices=["validate", "retrain", "eval", "generate"],
        help="Pipeline stages to run",
    )

    args = parser.parse_args()

    api = HfApi(token=os.environ.get("HF_TOKEN"))

    if args.command == "run":
        env_overrides = {}
        if args.env:
            for item in args.env:
                key, val = item.split("=", 1)
                env_overrides[key] = val
        trigger_job(api, args.config, env_overrides)

    elif args.command == "status":
        check_job_status(api, args.job_id)

    elif args.command == "pipeline":
        run_pipeline(api, args.stages)


if __name__ == "__main__":
    main()
