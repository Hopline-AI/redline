"""Zero-shot Mistral evaluation on the test set.

Runs extraction on each test sample using the Mistral API,
applies all scorers, and logs results to W&B.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from mistralai import Mistral

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
    """Extract policy text and expected JSON from a Mistral chat-format sample."""
    policy_text = ""
    expected = {}
    for msg in sample.get("messages", []):
        if msg["role"] == "user":
            policy_text = msg["content"]
        elif msg["role"] == "assistant":
            expected = json.loads(msg["content"])
    return policy_text, expected


def run_extraction(client: Mistral, model: str, policy_text: str) -> str:
    """Run zero-shot extraction via Mistral API."""
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


def evaluate(test_path: str, model: str = "open-mistral-7b", limit: int | None = None):
    """Run full baseline evaluation."""
    client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])
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

    # Try to import W&B
    try:
        import wandb
        wandb.init(
            project="redline-compliance",
            name=f"baseline-{model}",
            config={"model": model, "test_samples": len(samples), "phase": "baseline"},
        )
        use_wandb = True
    except (ImportError, wandb.Error):
        use_wandb = False
        print("W&B not available, logging to stdout only.")

    all_results = []

    for i, sample in enumerate(samples):
        policy_text, expected = extract_policy_and_expected(sample)
        print(f"[{i+1}/{len(samples)}] Extracting...", end=" ", flush=True)

        start = time.time()
        try:
            output = run_extraction(client, model, policy_text)
        except Exception as e:
            print(f"ERROR: {e}")
            output = "{}"
        latency = time.time() - start
        print(f"({latency:.1f}s)")

        result = {"sample_index": i, "latency_ms": latency * 1000}
        for name, scorer in scorers.items():
            result[name] = scorer.score(output, expected, policy_text)

        all_results.append(result)

    # Aggregate metrics
    n = len(all_results)
    agg = {
        "schema_validity_rate": sum(1 for r in all_results if r["schema"].get("schema_valid")) / n,
        "avg_field_accuracy": sum(r["fields"].get("field_accuracy", 0) for r in all_results) / n,
        "avg_precision": sum(r["rules"].get("precision", 0) for r in all_results) / n,
        "avg_recall": sum(r["rules"].get("recall", 0) for r in all_results) / n,
        "avg_f1": sum(r["rules"].get("f1", 0) for r in all_results) / n,
        "avg_source_overlap": sum(r["source"].get("source_text_overlap", 0) or 0 for r in all_results) / n,
        "avg_latency_ms": sum(r["latency_ms"] for r in all_results) / n,
    }

    print("\n--- Baseline Results ---")
    for k, v in agg.items():
        print(f"  {k}: {v:.4f}")

    # Save results to disk
    results_path = Path(__file__).parent / "baseline_results.json"
    results_payload = {
        "model": model,
        "phase": "baseline_zero_shot",
        "test_samples": n,
        "date": time.strftime("%Y-%m-%d"),
        "aggregate_metrics": agg,
        "per_sample": all_results,
    }
    with open(results_path, "w") as f:
        json.dump(results_payload, f, indent=2, default=str)
    print(f"\nResults saved to {results_path}")

    if use_wandb:
        wandb.log(agg)
        # Log per-sample table
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
        wandb.log({"baseline_results": table})
        wandb.finish()

    return agg, all_results


def main():
    parser = argparse.ArgumentParser(description="Run zero-shot baseline evaluation")
    parser.add_argument("--test-data", default="data/test.jsonl", help="Path to test JSONL")
    parser.add_argument("--model", default="open-mistral-7b", help="Mistral model name")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of samples")
    args = parser.parse_args()

    evaluate(args.test_data, args.model, args.limit)


if __name__ == "__main__":
    main()
