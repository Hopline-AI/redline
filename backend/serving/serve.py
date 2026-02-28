"""vLLM inference server for Redline.

Serves the fine-tuned LoRA adapter on top of the base model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def load_config(config_path: str = "serving/config.yaml") -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Start Redline vLLM inference server")
    parser.add_argument("--config", default="serving/config.yaml", help="Serving config")
    args = parser.parse_args()

    cfg = load_config(args.config)

    vllm_args = [
        "--model", cfg["server"]["base_model"],
        "--host", cfg["server"]["host"],
        "--port", str(cfg["server"]["port"]),
        "--tensor-parallel-size", str(cfg["server"]["tensor_parallel_size"]),
        "--max-model-len", str(cfg["server"]["max_model_len"]),
        "--gpu-memory-utilization", str(cfg["server"]["gpu_memory_utilization"]),
        "--max-num-seqs", str(cfg["batching"]["max_num_seqs"]),
        "--max-num-batched-tokens", str(cfg["batching"]["max_num_batched_tokens"]),
        "--enable-lora",
        "--lora-modules", f"redline-extractor={cfg['server']['model']}",
    ]

    print(f"Starting vLLM server...")
    print(f"Base model: {cfg['server']['base_model']}")
    print(f"LoRA adapter: {cfg['server']['model']}")
    print(f"Port: {cfg['server']['port']}")

    import subprocess
    import sys

    cmd = [sys.executable, "-m", "vllm.entrypoints.openai.api_server"] + vllm_args
    print(f"\nLaunching: {' '.join(cmd)}")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
