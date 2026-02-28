"""Evaluation scorers for Redline extraction quality.

Each scorer has a `score(output, expected, input_text) -> dict` interface.
Works standalone and integrates with W&B Weave when available.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "decision_logic.json"


def _load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def _parse_json(text: str) -> tuple[dict | None, str | None]:
    """Try to parse JSON from model output, handling markdown code fences.

    Returns (dict, None) on success or (None, error_string) on failure.
    If the parsed JSON is not a dict (e.g. a list), returns None with an error.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            return None, f"expected JSON object, got {type(parsed).__name__}"
        return parsed, None
    except json.JSONDecodeError as e:
        return None, str(e)


def _conditions_signature(rule: dict) -> tuple[str, ...]:
    conds = rule.get("conditions", [])
    return tuple(sorted(json.dumps(c, sort_keys=True) for c in conds))


def _action_signature(rule: dict) -> str:
    return json.dumps(rule.get("action", {}), sort_keys=True)


def _structure_signature(rule: dict) -> tuple:
    return (
        rule.get("condition_logic"),
        _conditions_signature(rule),
        _action_signature(rule),
    )


def _align_rules(expected_rules: list[dict], output_rules: list[dict]) -> tuple[list[tuple[dict, dict]], list[dict], list[dict]]:
    """Align expected/output rules with id-first then structural matching.

    Returns: (matched_pairs, unmatched_expected, unmatched_output)
    """
    matched: list[tuple[dict, dict]] = []
    used_out: set[int] = set()
    remaining_exp: list[int] = []

    # Pass 1: exact rule_id match.
    out_id_to_idx: dict[str, list[int]] = {}
    for oi, out_rule in enumerate(output_rules):
        rid = out_rule.get("rule_id")
        if rid:
            out_id_to_idx.setdefault(rid, []).append(oi)

    for exp_rule in expected_rules:
        rid = exp_rule.get("rule_id")
        matched_idx = None
        if rid and rid in out_id_to_idx:
            for oi in out_id_to_idx[rid]:
                if oi not in used_out:
                    matched_idx = oi
                    break
        if matched_idx is None:
            remaining_exp.append(len(matched))
            matched.append((exp_rule, None))
        else:
            used_out.add(matched_idx)
            matched.append((exp_rule, output_rules[matched_idx]))

    # Pass 2: structural match for unmatched expected rules.
    out_struct_to_idx: dict[tuple, list[int]] = {}
    for oi, out_rule in enumerate(output_rules):
        if oi in used_out:
            continue
        out_struct_to_idx.setdefault(_structure_signature(out_rule), []).append(oi)

    for pos in remaining_exp:
        exp_rule, out_rule = matched[pos]
        if out_rule is not None:
            continue
        sig = _structure_signature(exp_rule)
        candidate_idx = None
        for oi in out_struct_to_idx.get(sig, []):
            if oi not in used_out:
                candidate_idx = oi
                break
        if candidate_idx is not None:
            used_out.add(candidate_idx)
            matched[pos] = (exp_rule, output_rules[candidate_idx])

    matched_pairs = [(exp, out) for exp, out in matched if out is not None]
    unmatched_expected = [exp for exp, out in matched if out is None]
    unmatched_output = [output_rules[i] for i in range(len(output_rules)) if i not in used_out]
    return matched_pairs, unmatched_expected, unmatched_output


class SchemaValidityScorer:
    """Check if output is valid JSON matching the decision_logic schema."""

    def __init__(self):
        self.schema = _load_schema()

    def score(self, output: str, expected: dict | None = None, input_text: str = "") -> dict:
        parsed, parse_error = _parse_json(output)

        if parsed is None:
            return {
                "schema_valid": False,
                "json_parseable": False,
                "parse_error": parse_error,
            }

        try:
            jsonschema.validate(instance=parsed, schema=self.schema)
            return {"schema_valid": True, "json_parseable": True}
        except jsonschema.ValidationError as e:
            return {
                "schema_valid": False,
                "json_parseable": True,
                "validation_error": e.message,
                "error_path": list(e.absolute_path),
            }


class FieldAccuracyScorer:
    """Per-field exact match between output and expected extraction."""

    def score(self, output: str, expected: dict | None = None, input_text: str = "") -> dict:
        if expected is None:
            return {"field_accuracy": None, "error": "no expected output provided"}

        parsed, parse_error = _parse_json(output)
        if parsed is None:
            return {"field_accuracy": 0.0, "parse_error": parse_error}

        out_rules = parsed.get("rules", [])
        exp_rules = expected.get("rules", [])

        if not exp_rules:
            return {"field_accuracy": 1.0 if not out_rules else 0.0}

        matched_pairs, unmatched_expected, _ = _align_rules(exp_rules, out_rules)
        matched_exp_ids = {id(exp): out for exp, out in matched_pairs}

        fields_to_check = ["rule_type", "condition_logic"]
        total_checks = 0
        correct_checks = 0

        for exp_rule in exp_rules:
            out_rule = matched_exp_ids.get(id(exp_rule))
            if out_rule is None:
                total_checks += len(fields_to_check) + 2  # +2 for conditions, action
                continue

            # Simple fields
            for field_name in fields_to_check:
                total_checks += 1
                if exp_rule.get(field_name) == out_rule.get(field_name):
                    correct_checks += 1

            # Conditions match
            total_checks += 1
            exp_conds = sorted(json.dumps(c, sort_keys=True) for c in exp_rule.get("conditions", []))
            out_conds = sorted(json.dumps(c, sort_keys=True) for c in out_rule.get("conditions", []))
            if exp_conds == out_conds:
                correct_checks += 1

            # Action match
            total_checks += 1
            exp_action = json.dumps(exp_rule.get("action", {}), sort_keys=True)
            out_action = json.dumps(out_rule.get("action", {}), sort_keys=True)
            if exp_action == out_action:
                correct_checks += 1

        accuracy = correct_checks / total_checks if total_checks > 0 else 0.0

        total_rules = len(exp_rules)
        matched_count = len(matched_pairs)
        rule_type_correct = sum(1 for exp, out in matched_pairs if exp.get("rule_type") == out.get("rule_type"))
        cond_correct = sum(
            1
            for exp, out in matched_pairs
            if _conditions_signature(exp) == _conditions_signature(out)
        )
        action_correct = sum(
            1
            for exp, out in matched_pairs
            if _action_signature(exp) == _action_signature(out)
        )

        return {
            "field_accuracy": accuracy,
            "correct_fields": correct_checks,
            "total_fields": total_checks,
            "rule_type_accuracy": (rule_type_correct / total_rules) if total_rules else 1.0,
            "conditions_accuracy": (cond_correct / total_rules) if total_rules else 1.0,
            "action_accuracy": (action_correct / total_rules) if total_rules else 1.0,
            "matched_rules": matched_count,
            "missing_rules": len(unmatched_expected),
        }


class RuleDetectionScorer:
    """Precision and recall on rule count detection."""

    def score(self, output: str, expected: dict | None = None, input_text: str = "") -> dict:
        if expected is None:
            return {"rule_detection": None, "error": "no expected output provided"}

        parsed, parse_error = _parse_json(output)
        if parsed is None:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "parse_error": parse_error}

        out_rules = parsed.get("rules", [])
        exp_rules = expected.get("rules", [])
        matched_pairs, unmatched_expected, unmatched_output = _align_rules(exp_rules, out_rules)

        true_positives = len(matched_pairs)
        precision = true_positives / len(out_rules) if out_rules else 0.0
        recall = true_positives / len(exp_rules) if exp_rules else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "expected_count": len(exp_rules),
            "output_count": len(out_rules),
            "true_positives": true_positives,
            "hallucinated_rules": len(unmatched_output),
            "missed_rules": len(unmatched_expected),
        }


class SourceTextOverlapScorer:
    """Check that source_text fields appear verbatim in the input policy text."""

    def score(self, output: str, expected: dict | None = None, input_text: str = "") -> dict:
        parsed, parse_error = _parse_json(output)
        if parsed is None:
            return {"source_text_overlap": 0.0, "parse_error": parse_error}

        if not input_text:
            return {"source_text_overlap": None, "error": "no input_text provided"}

        rules = parsed.get("rules", [])
        if not rules:
            return {"source_text_overlap": 1.0, "total_rules": 0}

        matches = 0
        for rule in rules:
            source = rule.get("source_text", "")
            if source and source in input_text:
                matches += 1

        return {
            "source_text_overlap": matches / len(rules),
            "matched": matches,
            "total_rules": len(rules),
        }


class ConfidenceCalibrationScorer:
    """Check if confidence tags correlate with actual correctness."""

    def score(self, output: str, expected: dict | None = None, input_text: str = "") -> dict:
        if expected is None:
            return {"confidence_calibration": None, "error": "no expected output"}

        parsed, parse_error = _parse_json(output)
        if parsed is None:
            return {"confidence_calibration": 0.0, "parse_error": parse_error}

        out_rules = parsed.get("rules", [])
        exp_rules = expected.get("rules", [])
        matched_pairs, _, _ = _align_rules(exp_rules, out_rules)
        matched_out = {id(out) for _, out in matched_pairs}

        buckets: dict[str, dict[str, int]] = {
            "high": {"correct": 0, "total": 0},
            "medium": {"correct": 0, "total": 0},
            "low": {"correct": 0, "total": 0},
        }

        for rule in out_rules:
            confidence = rule.get("confidence", "medium")
            if confidence not in buckets:
                confidence = "medium"
            buckets[confidence]["total"] += 1

            if id(rule) in matched_out:
                buckets[confidence]["correct"] += 1

        calibration = {}
        for level, counts in buckets.items():
            if counts["total"] > 0:
                calibration[level] = counts["correct"] / counts["total"]
            else:
                calibration[level] = None

        # Well-calibrated means high > medium > low in accuracy
        return {
            "confidence_calibration": calibration,
            "bucket_counts": {k: v["total"] for k, v in buckets.items()},
        }


class FailureModeScorer:
    """Categorize extraction errors by type."""

    FAILURE_TYPES = [
        "missing_field", "wrong_operator", "hallucinated_rule", "malformed_json",
        "wrong_value", "extra_field", "wrong_rule_type", "missing_rule",
    ]

    def score(self, output: str, expected: dict | None = None, input_text: str = "") -> dict:
        parsed, parse_error = _parse_json(output)

        failures: dict[str, int] = {ft: 0 for ft in self.FAILURE_TYPES}

        if parsed is None:
            failures["malformed_json"] = 1
            return {"failure_modes": failures, "total_failures": 1, "parse_error": parse_error}

        if expected is None:
            return {"failure_modes": failures, "total_failures": 0}

        out_rules = parsed.get("rules", [])
        exp_rules = expected.get("rules", [])
        matched_pairs, unmatched_expected, unmatched_output = _align_rules(exp_rules, out_rules)

        failures["hallucinated_rule"] += len(unmatched_output)
        failures["missing_rule"] += len(unmatched_expected)

        for exp_rule, out_rule in matched_pairs:

            if exp_rule.get("rule_type") != out_rule.get("rule_type"):
                failures["wrong_rule_type"] += 1

            # Check conditions
            exp_conds = exp_rule.get("conditions", [])
            out_conds = out_rule.get("conditions", [])
            for ec in exp_conds:
                matched = False
                for oc in out_conds:
                    if ec.get("field") == oc.get("field"):
                        matched = True
                        if ec.get("operator") != oc.get("operator"):
                            failures["wrong_operator"] += 1
                        if ec.get("value") != oc.get("value"):
                            failures["wrong_value"] += 1
                        break
                if not matched:
                    failures["missing_field"] += 1

            # Extra conditions not in expected
            exp_fields = {c.get("field") for c in exp_conds}
            for oc in out_conds:
                if oc.get("field") not in exp_fields:
                    failures["extra_field"] += 1

        total = sum(failures.values())
        return {"failure_modes": failures, "total_failures": total}
