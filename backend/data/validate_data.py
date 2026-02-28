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
    total_rules = 0

    for sample in samples:
        parsed, _ = extract_assistant_json(sample)
        if parsed is None:
            continue
        for rule in parsed.get("rules", []):
            rule_types[rule.get("rule_type", "unknown")] += 1
            total_rules += 1
        for j in parsed.get("metadata", {}).get("applicable_jurisdictions", []):
            jurisdictions[j] += 1

    return {
        "total_samples": len(samples),
        "total_rules": total_rules,
        "rule_type_distribution": dict(rule_types.most_common()),
        "jurisdiction_distribution": dict(jurisdictions.most_common()),
    }


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
    print(f"   Jurisdictions:")
    for j, count in dist["jurisdiction_distribution"].items():
        print(f"     {j}: {count}")

    total_failures = f + f2 + f3
    print(f"\n{'PASS' if total_failures == 0 else 'FAIL'}: {total_failures} total failures")
    sys.exit(0 if total_failures == 0 else 1)


if __name__ == "__main__":
    main()
