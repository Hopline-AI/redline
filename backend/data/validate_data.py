#!/usr/bin/env python3
"""Validate synthetic training data for Redline compliance extraction.

4 checks:
1. JSON parsability — assistant content must be valid JSON
2. Schema validation — must match decision_logic.json schema
3. Source text verbatim — every source_text must appear in the input policy
4. Distribution — even coverage across rule_types and topics
"""

import argparse
import json
import re
import sys
from collections import Counter
import jsonschema


def load_schema(schema_path: str) -> dict:
    with open(schema_path) as f:
        return json.load(f)


def load_jsonl(path: str) -> list[dict]:
    samples = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                samples.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  FAIL line {i}: invalid JSONL — {e}")
    return samples


def extract_policy_text(sample: dict) -> str | None:
    """Extract the user's policy text from a Mistral chat-format sample."""
    for msg in sample.get("messages", []):
        if msg.get("role") == "user":
            return msg["content"]
    return None


def extract_assistant_json(sample: dict) -> tuple[dict | None, str | None]:
    """Parse the assistant's response as JSON. Returns (parsed, error)."""
    for msg in sample.get("messages", []):
        if msg.get("role") == "assistant":
            content = msg["content"]
            try:
                return json.loads(content), None
            except json.JSONDecodeError as e:
                return None, str(e)
    return None, "no assistant message found"


def check_json_parsability(samples: list[dict]) -> tuple[int, int, list[str]]:
    passed = 0
    failed = 0
    errors = []
    for i, sample in enumerate(samples):
        parsed, err = extract_assistant_json(sample)
        if parsed is not None:
            passed += 1
        else:
            failed += 1
            errors.append(f"  sample {i}: {err}")
    return passed, failed, errors


def check_schema_validity(samples: list[dict], schema: dict) -> tuple[int, int, list[str]]:
    passed = 0
    failed = 0
    errors = []
    for i, sample in enumerate(samples):
        parsed, _ = extract_assistant_json(sample)
        if parsed is None:
            failed += 1
            errors.append(f"  sample {i}: skipped (not valid JSON)")
            continue
        try:
            jsonschema.validate(instance=parsed, schema=schema)
            passed += 1
        except jsonschema.ValidationError as e:
            failed += 1
            errors.append(f"  sample {i}: {e.message} (path: {list(e.absolute_path)})")
    return passed, failed, errors


def check_source_text(samples: list[dict]) -> tuple[int, int, list[str]]:
    passed = 0
    failed = 0
    errors = []
    for i, sample in enumerate(samples):
        policy_text = extract_policy_text(sample)
        parsed, _ = extract_assistant_json(sample)
        if parsed is None or policy_text is None:
            failed += 1
            errors.append(f"  sample {i}: skipped (missing data)")
            continue

        sample_ok = True
        for j, rule in enumerate(parsed.get("rules", [])):
            source = rule.get("source_text", "")
            if source not in policy_text:
                sample_ok = False
                errors.append(
                    f"  sample {i}, rule {j} ({rule.get('rule_id', '?')}): "
                    f"source_text not found verbatim in policy"
                )
        if sample_ok:
            passed += 1
        else:
            failed += 1
    return passed, failed, errors


def check_distribution(samples: list[dict]) -> dict:
    rule_types = Counter()
    jurisdictions = Counter()
    operators = Counter()
    confidence = Counter()
    condition_logic = Counter()
    total_rules = 0
    total_conditions = 0

    for sample in samples:
        parsed, _ = extract_assistant_json(sample)
        if parsed is None:
            continue
        for rule in parsed.get("rules", []):
            rule_types[rule.get("rule_type", "unknown")] += 1
            condition_logic[rule.get("condition_logic", "unknown")] += 1
            confidence[rule.get("confidence", "missing")] += 1
            for cond in rule.get("conditions", []):
                operators[cond.get("operator", "unknown")] += 1
                total_conditions += 1
            total_rules += 1
        for j in parsed.get("metadata", {}).get("applicable_jurisdictions", []):
            jurisdictions[j] += 1

    return {
        "total_samples": len(samples),
        "total_rules": total_rules,
        "total_conditions": total_conditions,
        "rule_type_distribution": dict(rule_types.most_common()),
        "operator_distribution": dict(operators.most_common()),
        "confidence_distribution": dict(confidence.most_common()),
        "condition_logic_distribution": dict(condition_logic.most_common()),
        "jurisdiction_distribution": dict(jurisdictions.most_common()),
    }


def check_quality_gates(samples: list[dict], dist: dict, args) -> tuple[int, int, list[str]]:
    """Production data quality gates for balance and diversity."""
    errors = []
    checks = 0

    total_rules = dist["total_rules"]
    total_conditions = dist["total_conditions"]
    logic = dist["condition_logic_distribution"]
    confidence = dist["confidence_distribution"]
    operators = dist["operator_distribution"]

    if total_rules == 0:
        return 0, 1, ["  quality_gates: no rules found"]

    any_ratio = logic.get("any", 0) / total_rules
    checks += 1
    if any_ratio < args.min_any_ratio:
        errors.append(
            f"  quality_gates: condition_logic 'any' ratio {any_ratio:.4f} < {args.min_any_ratio:.4f}"
        )

    low_conf_ratio = confidence.get("low", 0) / total_rules
    checks += 1
    if low_conf_ratio < args.min_low_conf_ratio:
        errors.append(
            f"  quality_gates: confidence 'low' ratio {low_conf_ratio:.4f} < {args.min_low_conf_ratio:.4f}"
        )

    if total_conditions > 0:
        eq_ratio = operators.get("eq", 0) / total_conditions
    else:
        eq_ratio = 1.0
    checks += 1
    if eq_ratio > args.max_eq_ratio:
        errors.append(
            f"  quality_gates: operator 'eq' ratio {eq_ratio:.4f} > {args.max_eq_ratio:.4f}"
        )

    checks += 1
    not_in_presence = operators.get("not_in", 0) / max(1, total_conditions)
    if not_in_presence < args.min_not_in_ratio:
        errors.append(
            f"  quality_gates: operator 'not_in' ratio {not_in_presence:.4f} < {args.min_not_in_ratio:.4f}"
        )

    iso_date = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    non_iso = 0
    for sample in samples:
        parsed, _ = extract_assistant_json(sample)
        if parsed is None:
            continue
        eff = parsed.get("metadata", {}).get("effective_date", "")
        if not iso_date.match(eff):
            non_iso += 1
    checks += 1
    if non_iso > 0:
        errors.append(f"  quality_gates: non-ISO effective_date found in {non_iso} samples")

    return checks - len(errors), len(errors), errors


def main():
    parser = argparse.ArgumentParser(description="Validate Redline training data")
    parser.add_argument("data_path", help="Path to JSONL file to validate")
    parser.add_argument(
        "--schema",
        default="schema/decision_logic.json",
        help="Path to JSON schema (default: schema/decision_logic.json)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show individual errors"
    )
    parser.add_argument("--quality-gates", action="store_true", help="Enable production quality gates")
    parser.add_argument("--min-any-ratio", type=float, default=0.03, help="Minimum ratio of condition_logic='any'")
    parser.add_argument("--min-low-conf-ratio", type=float, default=0.01, help="Minimum ratio of confidence='low'")
    parser.add_argument("--max-eq-ratio", type=float, default=0.70, help="Maximum ratio of operator='eq'")
    parser.add_argument("--min-not-in-ratio", type=float, default=0.01, help="Minimum ratio of operator='not_in'")
    args = parser.parse_args()

    schema = load_schema(args.schema)
    samples = load_jsonl(args.data_path)

    if not samples:
        print(f"ERROR: No samples loaded from {args.data_path}")
        sys.exit(1)

    print(f"Loaded {len(samples)} samples from {args.data_path}\n")

    # Check 1: JSON parsability
    p, f, errs = check_json_parsability(samples)
    print(f"1. JSON parsability:    {p} passed / {f} failed")
    if args.verbose and errs:
        for e in errs[:10]:
            print(e)

    # Check 2: Schema validity
    p2, f2, errs2 = check_schema_validity(samples, schema)
    print(f"2. Schema validity:     {p2} passed / {f2} failed")
    if args.verbose and errs2:
        for e in errs2[:10]:
            print(e)

    # Check 3: Source text verbatim
    p3, f3, errs3 = check_source_text(samples)
    print(f"3. Source text check:   {p3} passed / {f3} failed")
    if args.verbose and errs3:
        for e in errs3[:10]:
            print(e)

    # Check 4: Distribution
    dist = check_distribution(samples)
    print(f"\n4. Distribution:")
    print(f"   Total samples: {dist['total_samples']}")
    print(f"   Total rules:   {dist['total_rules']}")
    print(f"   Rule types:")
    for rt, count in dist["rule_type_distribution"].items():
        print(f"     {rt}: {count}")
    print(f"   Operators:")
    for op, count in dist["operator_distribution"].items():
        print(f"     {op}: {count}")
    print(f"   Condition logic:")
    for logic_key, count in dist["condition_logic_distribution"].items():
        print(f"     {logic_key}: {count}")
    print(f"   Confidence:")
    for conf_key, count in dist["confidence_distribution"].items():
        print(f"     {conf_key}: {count}")
    print(f"   Jurisdictions:")
    for j, count in dist["jurisdiction_distribution"].items():
        print(f"     {j}: {count}")

    f4 = 0
    if args.quality_gates:
        p4, f4, errs4 = check_quality_gates(samples, dist, args)
        print(f"5. Quality gates:       {p4} passed / {f4} failed")
        if errs4:
            for e in errs4:
                print(e)

    total_failures = f + f2 + f3 + f4
    print(f"\n{'PASS' if total_failures == 0 else 'FAIL'}: {total_failures} total failures")
    sys.exit(0 if total_failures == 0 else 1)


if __name__ == "__main__":
    main()
