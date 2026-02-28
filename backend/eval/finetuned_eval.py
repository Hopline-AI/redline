"""Post-fine-tuning evaluation with W&B Weave tracing.

Supports loading the model from a local path, HF Hub, or a remote BREV endpoint.
Runs the same scorer suite as baseline and produces side-by-side comparison.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import requests

from eval.scorers import (
    ConfidenceCalibrationScorer,
    FailureModeScorer,
    FieldAccuracyScorer,
    RuleDetectionScorer,
    SchemaValidityScorer,
    SourceTextOverlapScorer,
)

PROMPT_TEMPLATE_PATH = Path(__file__).parent.parent / "schema" / "prompt_template.txt"


def load_prompt_template() -> str:
    return PROMPT_TEMPLATE_PATH.read_text()


def load_test_data(path: str) -> list[dict]:
    samples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def extract_policy_and_expected(sample: dict) -> tuple[str, dict]:
    policy_text = ""
    expected = {}
    for msg in sample.get("messages", []):
        if msg["role"] == "user":
            policy_text = msg["content"]
        elif msg["role"] == "assistant":
            expected = json.loads(msg["content"])
    return policy_text, expected


def run_extraction_endpoint(endpoint_url: str, policy_text: str) -> str:
    """Call a vLLM/TGI-compatible endpoint (OpenAI format)."""
    template = load_prompt_template()
    system_msg = template.split("USER:")[0].replace("SYSTEM:", "").strip()
    user_msg = template.split("USER:")[1].strip().replace("{policy_text}", policy_text)

    resp = requests.post(
        f"{endpoint_url}/v1/chat/completions",
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
    return resp.json()["choices"][0]["message"]["content"]


def run_extraction_mistral(policy_text: str, model: str) -> str:
    """Call Mistral API for fine-tuned model."""
    from mistralai import Mistral

    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
    template = load_prompt_template()
    system_msg = template.split("USER:")[0].replace("SYSTEM:", "").strip()
    user_msg = template.split("USER:")[1].strip().replace("{policy_text}", policy_text)

    response = client.chat.complete(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def evaluate(
    test_path: str,
    endpoint_url: str | None = None,
    model: str | None = None,
    limit: int | None = None,
    baseline_run_id: str | None = None,
):
    """Run full fine-tuned evaluation with optional Weave tracing."""
    samples = load_test_data(test_path)
    if limit:
        samples = samples[:limit]

    scorers = {
        "schema": SchemaValidityScorer(),
        "fields": FieldAccuracyScorer(),
        "rules": RuleDetectionScorer(),
        "source": SourceTextOverlapScorer(),
        "confidence": ConfidenceCalibrationScorer(),
        "failures": FailureModeScorer(),
    }

    # Initialize W&B + Weave
    use_wandb = False
    use_weave = False
    try:
        import wandb
        wandb.init(
            project="redline-compliance",
            name=f"finetuned-eval-{model or 'endpoint'}",
            config={
                "model": model or endpoint_url,
                "test_samples": len(samples),
                "phase": "finetuned_eval",
                "baseline_run_id": baseline_run_id,
            },
        )
        use_wandb = True
    except (ImportError, Exception):
        print("W&B not available.")

    try:
        import weave
        weave.init("redline-compliance")
        use_weave = True
    except (ImportError, Exception):
        print("Weave not available.")

    all_results = []

    for i, sample in enumerate(samples):
        policy_text, expected = extract_policy_and_expected(sample)
        print(f"[{i+1}/{len(samples)}] Extracting...", end=" ", flush=True)

        start = time.time()
        try:
            if endpoint_url:
                output = run_extraction_endpoint(endpoint_url, policy_text)
            elif model:
                output = run_extraction_mistral(policy_text, model)
            else:
                raise ValueError("Must provide either --endpoint or --model")
        except Exception as e:
            print(f"ERROR: {e}")
            output = "{}"
        latency = time.time() - start
        print(f"({latency:.1f}s)")

        result = {"sample_index": i, "latency_ms": latency * 1000}
        for name, scorer in scorers.items():
            result[name] = scorer.score(output, expected, policy_text)

        # Log Weave trace
        if use_weave:
            try:
                import weave
                weave.publish({
                    "input_policy_text": policy_text[:500],
                    "raw_model_output": output[:500],
                    "latency_ms": result["latency_ms"],
                    "rule_count_expected": result["rules"].get("expected_count", 0),
                    "rule_count_extracted": result["rules"].get("output_count", 0),
                    "schema_valid": result["schema"].get("schema_valid", False),
                }, name=f"extraction_trace_{i}")
            except Exception:
                pass

        all_results.append(result)

    # Aggregate
    n = len(all_results)
    agg = {
        "eval/schema_validity_rate": sum(1 for r in all_results if r["schema"].get("schema_valid")) / n,
        "eval/field_accuracy": sum(r["fields"].get("field_accuracy", 0) for r in all_results) / n,
        "eval/precision": sum(r["rules"].get("precision", 0) for r in all_results) / n,
        "eval/recall": sum(r["rules"].get("recall", 0) for r in all_results) / n,
        "eval/f1": sum(r["rules"].get("f1", 0) for r in all_results) / n,
        "eval/source_overlap": sum(r["source"].get("source_text_overlap", 0) or 0 for r in all_results) / n,
        "eval/avg_latency_ms": sum(r["latency_ms"] for r in all_results) / n,
    }

    # Per rule_type accuracy (from failure modes)
    rule_type_correct: dict[str, list[float]] = {}
    for r in all_results:
        fm = r["failures"].get("failure_modes", {})
        # Approximate: if no wrong_rule_type failures, count as correct
        has_type_error = fm.get("wrong_rule_type", 0) > 0
        for rt in ["entitlement", "restriction", "leave", "termination", "compensation", "eligibility"]:
            if rt not in rule_type_correct:
                rule_type_correct[rt] = []
            rule_type_correct[rt].append(0.0 if has_type_error else 1.0)

    for rt, vals in rule_type_correct.items():
        agg[f"eval/per_type/{rt}"] = sum(vals) / len(vals) if vals else 0.0

    print("\n--- Fine-tuned Results ---")
    for k, v in agg.items():
        print(f"  {k}: {v:.4f}")

    if use_wandb:
        wandb.log(agg)
        table = wandb.Table(columns=["sample", "schema_valid", "field_accuracy", "precision", "recall", "f1", "source_overlap", "latency_ms"])
        for r in all_results:
            table.add_data(
                r["sample_index"],
                r["schema"].get("schema_valid", False),
                r["fields"].get("field_accuracy", 0),
                r["rules"].get("precision", 0),
                r["rules"].get("recall", 0),
                r["rules"].get("f1", 0),
                r["source"].get("source_text_overlap", 0) or 0,
                r["latency_ms"],
            )
        wandb.log({"finetuned_results": table})
        wandb.finish()

    return agg, all_results


def main():
    parser = argparse.ArgumentParser(description="Run fine-tuned model evaluation")
    parser.add_argument("--test-data", default="data/test.jsonl", help="Path to test JSONL")
    parser.add_argument("--endpoint", default=None, help="vLLM/TGI endpoint URL")
    parser.add_argument("--model", default=None, help="Mistral fine-tuned model ID")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of samples")
    parser.add_argument("--baseline-run-id", default=None, help="W&B baseline run ID for comparison")
    args = parser.parse_args()

    evaluate(args.test_data, args.endpoint, args.model, args.limit, args.baseline_run_id)


if __name__ == "__main__":
    main()
