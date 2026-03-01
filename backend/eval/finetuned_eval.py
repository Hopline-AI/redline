"""Post-fine-tuning evaluation using weave.Evaluation with W&B Models logging.

Primary path: weave.Evaluation with @weave.op() scorers — creates Weave traces and
a tracked evaluation visible in the Weave UI.

Fallback path: manual loop when Weave is unavailable, with identical W&B Models logging.
"""

from __future__ import annotations

import argparse
import asyncio
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
RULE_TYPES = ["entitlement", "restriction", "leave", "termination", "compensation", "eligibility"]

_local_model = None
_local_tokenizer = None


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


def load_local_model(adapter_path: str, base_model: str, max_seq_length: int = 4096):
    global _local_model, _local_tokenizer
    if _local_model is not None:
        return _local_model, _local_tokenizer

    from unsloth import FastLanguageModel

    print(f"Loading base model {base_model} + adapter from {adapter_path}...")
    _local_model, _local_tokenizer = FastLanguageModel.from_pretrained(
        model_name=adapter_path,
        max_seq_length=max_seq_length,
        load_in_4bit=True,
        dtype=None,
    )
    FastLanguageModel.for_inference(_local_model)
    print("Model loaded.")
    return _local_model, _local_tokenizer


def run_extraction_local(policy_text: str) -> str:
    model, tokenizer = _local_model, _local_tokenizer
    system_msg = (
        "You are a compliance extraction engine. Your task is to extract all decision "
        "rules from company policy documents into structured JSON. Output only valid JSON "
        "matching the provided schema. Do not interpret, evaluate, or offer opinions on "
        "the rules — only extract them exactly as stated in the policy text."
    )
    user_msg = (
        "Extract all decision rules from the following company policy into structured JSON. "
        "For each rule, identify the rule type, conditions, actions, and include the exact "
        f"source text from the policy.\n\nPolicy text:\n{policy_text}"
    )
    prompt = f"<s>[INST] {system_msg}\n{user_msg} [/INST]"
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=4096, temperature=0.0, do_sample=False)
    generated = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(generated, skip_special_tokens=True)


def run_extraction_endpoint(endpoint_url: str, policy_text: str) -> str:
    template = load_prompt_template()
    system_msg = template.split("USER:")[0].replace("SYSTEM:", "").strip()
    user_msg = template.split("USER:")[1].strip().replace("{policy_text}", policy_text)

    models_resp = requests.get(f"{endpoint_url}/v1/models", timeout=10)
    model_name = models_resp.json()["data"][0]["id"]

    resp = requests.post(
        f"{endpoint_url}/v1/chat/completions",
        json={
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.0,
            "max_tokens": 2048,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def run_extraction_mistral(policy_text: str, model: str) -> str:
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


def _manual_eval_loop(
    dataset_rows: list[dict],
    scorers: dict,
    endpoint_url: str | None,
    model: str | None,
    local_adapter: str | None,
) -> dict:
    """Fallback manual eval loop when Weave is unavailable."""
    all_results = []

    for i, row in enumerate(dataset_rows):
        policy_text = row["policy_text"]
        expected = row["expected"]
        print(f"[{i+1}/{len(dataset_rows)}] Extracting...", end=" ", flush=True)

        start = time.time()
        try:
            if local_adapter:
                output = run_extraction_local(policy_text)
            elif endpoint_url:
                output = run_extraction_endpoint(endpoint_url, policy_text)
            elif model:
                output = run_extraction_mistral(policy_text, model)
            else:
                raise ValueError("No inference mode configured")
        except Exception as e:
            print(f"ERROR: {e}")
            output = "{}"
        latency = time.time() - start
        print(f"({latency:.1f}s)")

        result = {"latency_ms": latency * 1000}
        for name, scorer in scorers.items():
            result[name] = scorer.score(output, expected, policy_text)
        all_results.append(result)

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

    # Per-type accuracy using FieldAccuracyScorer's per_type_accuracy output
    rule_type_scores: dict[str, list[float]] = {}
    for r in all_results:
        for rt, score in r["fields"].get("per_type_accuracy", {}).items():
            rule_type_scores.setdefault(rt, []).append(score)

    for rt in RULE_TYPES:
        vals = rule_type_scores.get(rt, [])
        agg[f"eval/per_type/{rt}"] = sum(vals) / len(vals) if vals else 0.0

    return agg


def evaluate(
    test_path: str,
    endpoint_url: str | None = None,
    model: str | None = None,
    local_adapter: str | None = None,
    base_model: str = "mistralai/Mistral-7B-Instruct-v0.3",
    limit: int | None = None,
    baseline_run_id: str | None = None,
):
    """Run full fine-tuned evaluation.

    Primary path: weave.Evaluation with @weave.op() scorers — creates Weave traces
    and a tracked evaluation in the Weave UI, then logs summary metrics to W&B Models.

    Fallback: manual loop with identical W&B Models logging when Weave is unavailable.
    """
    samples = load_test_data(test_path)
    if limit:
        samples = samples[:limit]

    if local_adapter:
        load_local_model(local_adapter, base_model)

    run_name = f"finetuned-eval-{local_adapter or model or 'endpoint'}"

    scorers = {
        "schema": SchemaValidityScorer(),
        "fields": FieldAccuracyScorer(),
        "rules": RuleDetectionScorer(),
        "source": SourceTextOverlapScorer(),
        "confidence": ConfidenceCalibrationScorer(),
        "failures": FailureModeScorer(),
    }

    dataset_rows = [
        {"policy_text": pt, "expected": exp}
        for pt, exp in (extract_policy_and_expected(s) for s in samples)
    ]

    # W&B Models init
    use_wandb = False
    try:
        import wandb
        wandb.init(
            project="redline-compliance",
            name=run_name,
            config={
                "model": model or local_adapter or endpoint_url,
                "test_samples": len(samples),
                "phase": "finetuned_eval",
                "baseline_run_id": baseline_run_id,
                "inference_mode": "local" if local_adapter else ("endpoint" if endpoint_url else "api"),
            },
        )
        use_wandb = True
    except (ImportError, Exception):
        print("W&B not available.")

    # --- Primary path: Weave Evaluation ---
    agg = {}
    use_weave = False

    try:
        import weave as _weave
        _weave.init("redline-compliance")

        _schema_s = scorers["schema"]
        _field_s = scorers["fields"]
        _rule_s = scorers["rules"]
        _source_s = scorers["source"]

        @_weave.op()
        def extraction_model(policy_text: str) -> str:
            start = time.time()
            try:
                if local_adapter:
                    out = run_extraction_local(policy_text)
                elif endpoint_url:
                    out = run_extraction_endpoint(endpoint_url, policy_text)
                elif model:
                    out = run_extraction_mistral(policy_text, model)
                else:
                    raise ValueError("No inference mode configured")
            except Exception as exc:
                print(f"  Inference error: {exc}")
                out = "{}"
            print(f"  [{time.time() - start:.1f}s]")
            return out

        @_weave.op()
        def schema_validity(output: str) -> dict:
            return _schema_s.score(output)

        @_weave.op()
        def field_accuracy(output: str, expected: dict) -> dict:
            return _field_s.score(output, expected)

        @_weave.op()
        def rule_detection(output: str, expected: dict) -> dict:
            return _rule_s.score(output, expected)

        @_weave.op()
        def source_overlap(output: str, policy_text: str) -> dict:
            return _source_s.score(output, input_text=policy_text)

        weave_eval = _weave.Evaluation(
            name="redline-extraction-eval",
            dataset=dataset_rows,
            scorers=[schema_validity, field_accuracy, rule_detection, source_overlap],
        )

        print(f"\nRunning Weave Evaluation ({len(dataset_rows)} samples)...")
        summary = asyncio.run(weave_eval.evaluate(extraction_model))
        use_weave = True
        print(f"Weave Evaluation complete.")

        print(f"\nWeave summary keys: {list(summary.keys())}")
        for k, v in summary.items():
            print(f"  {k}: {v}")

        # Parse summary — weave aggregates differently by return type:
        # floats → {"mean": val}, booleans → {"true_fraction": val, "true_count": n}
        def _mean(scorer: str, metric: str) -> float:
            val = summary.get(scorer, {}).get(metric)
            if isinstance(val, dict):
                for key in ("mean", "true_fraction", "true_mean"):
                    if key in val:
                        return float(val[key])
                return 0.0
            return float(val) if val is not None else 0.0

        agg = {
            "eval/schema_validity_rate": _mean("schema_validity", "schema_valid"),
            "eval/field_accuracy": _mean("field_accuracy", "field_accuracy"),
            "eval/precision": _mean("rule_detection", "precision"),
            "eval/recall": _mean("rule_detection", "recall"),
            "eval/f1": _mean("rule_detection", "f1"),
            "eval/source_overlap": _mean("source_overlap", "source_text_overlap"),
            "eval/avg_latency_ms": 0.0,
        }

        # Per-type: FieldAccuracyScorer now returns per_type_accuracy dict per sample.
        # Weave aggregates nested dict values keyed by rule_type.
        pt_summary = summary.get("field_accuracy", {}).get("per_type_accuracy", {})
        for rt in RULE_TYPES:
            val = pt_summary.get(rt)
            if isinstance(val, dict):
                agg[f"eval/per_type/{rt}"] = float(val.get("mean", 0.0))
            elif val is not None:
                agg[f"eval/per_type/{rt}"] = float(val)
            else:
                agg[f"eval/per_type/{rt}"] = 0.0

    except Exception as exc:
        print(f"Weave Evaluation failed ({exc}), falling back to manual eval loop.")
        agg = _manual_eval_loop(dataset_rows, scorers, endpoint_url, model, local_adapter)

    print("\n--- Eval Results ---")
    for k, v in sorted(agg.items()):
        print(f"  {k}: {v:.4f}")

    if use_wandb:
        import wandb
        wandb.log(agg)
        wandb.finish()

    return agg, []


def main():
    parser = argparse.ArgumentParser(description="Run fine-tuned model evaluation")
    parser.add_argument("--test-data", default="data/test.jsonl")
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--local-adapter", default=None)
    parser.add_argument("--base-model", default="mistralai/Mistral-7B-Instruct-v0.3")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--baseline-run-id", default=None)
    args = parser.parse_args()

    evaluate(args.test_data, args.endpoint, args.model, args.local_adapter, args.base_model, args.limit, args.baseline_run_id)


if __name__ == "__main__":
    main()
