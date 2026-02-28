"""vLLM inference server with constrained JSON decoding for Redline.

Serves the fine-tuned model with outlines-based guided decoding to
guarantee valid JSON output matching the decision_logic schema.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def load_config(config_path: str = "serving/config.yaml") -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_schema(schema_path: str) -> dict:
    with open(schema_path) as f:
        return json.load(f)


def build_prompt(policy_text: str) -> list[dict]:
    """Build chat messages from policy text using the prompt template."""
    template_path = Path(__file__).parent.parent / "schema" / "prompt_template.txt"
    template = template_path.read_text()
    system_msg = template.split("USER:")[0].replace("SYSTEM:", "").strip()
    user_msg = template.split("USER:")[1].strip().replace("{policy_text}", policy_text)
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def main():
    parser = argparse.ArgumentParser(description="Start Redline vLLM inference server")
    parser.add_argument("--config", default="serving/config.yaml", help="Serving config")
    args = parser.parse_args()

    cfg = load_config(args.config)

    from vllm import LLM, SamplingParams
    from vllm.entrypoints.openai.api_server import run_server

    schema = load_schema(cfg["decoding"]["schema_path"])

    # Build vLLM launch args
    vllm_args = [
        "--model", cfg["server"]["model"],
        "--host", cfg["server"]["host"],
        "--port", str(cfg["server"]["port"]),
        "--tensor-parallel-size", str(cfg["server"]["tensor_parallel_size"]),
        "--max-model-len", str(cfg["server"]["max_model_len"]),
        "--gpu-memory-utilization", str(cfg["server"]["gpu_memory_utilization"]),
        "--max-num-seqs", str(cfg["batching"]["max_num_seqs"]),
        "--max-num-batched-tokens", str(cfg["batching"]["max_num_batched_tokens"]),
    ]

    if cfg["quantization"]["method"] != "none":
        vllm_args.extend(["--quantization", cfg["quantization"]["method"]])

    if cfg["decoding"]["guided_json"]:
        vllm_args.extend([
            "--guided-decoding-backend", cfg["decoding"]["backend"],
        ])

    print(f"Starting vLLM server with args: {' '.join(vllm_args)}")
    print(f"Constrained decoding: {cfg['decoding']['guided_json']} (backend: {cfg['decoding']['backend']})")
    print(f"Schema: {cfg['decoding']['schema_path']}")

    # Use subprocess to launch vLLM OpenAI-compatible server
    import subprocess
    import sys

    cmd = [sys.executable, "-m", "vllm.entrypoints.openai.api_server"] + vllm_args
    print(f"\nLaunching: {' '.join(cmd)}")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
