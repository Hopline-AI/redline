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

        # Match rules by rule_id for comparison
        exp_by_id = {r["rule_id"]: r for r in exp_rules}
        out_by_id = {r.get("rule_id"): r for r in out_rules}

        fields_to_check = ["rule_type", "condition_logic"]
        total_checks = 0
        correct_checks = 0

        for rule_id, exp_rule in exp_by_id.items():
            out_rule = out_by_id.get(rule_id)
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

        return {
            "field_accuracy": accuracy,
            "correct_fields": correct_checks,
            "total_fields": total_checks,
            "rule_type_accuracy": self._field_accuracy(exp_by_id, out_by_id, "rule_type"),
            "conditions_accuracy": self._conditions_accuracy(exp_by_id, out_by_id),
            "action_accuracy": self._action_accuracy(exp_by_id, out_by_id),
        }

    @staticmethod
    def _field_accuracy(exp_by_id: dict, out_by_id: dict, field: str) -> float:
        total = len(exp_by_id)
        if total == 0:
            return 1.0
        correct = sum(
            1 for rid, exp in exp_by_id.items()
            if rid in out_by_id and out_by_id[rid].get(field) == exp.get(field)
        )
        return correct / total

    @staticmethod
    def _conditions_accuracy(exp_by_id: dict, out_by_id: dict) -> float:
        total = len(exp_by_id)
        if total == 0:
            return 1.0
        correct = 0
        for rid, exp in exp_by_id.items():
            if rid not in out_by_id:
                continue
            exp_c = sorted(json.dumps(c, sort_keys=True) for c in exp.get("conditions", []))
            out_c = sorted(json.dumps(c, sort_keys=True) for c in out_by_id[rid].get("conditions", []))
            if exp_c == out_c:
                correct += 1
        return correct / total

    @staticmethod
    def _action_accuracy(exp_by_id: dict, out_by_id: dict) -> float:
        total = len(exp_by_id)
        if total == 0:
            return 1.0
        correct = 0
        for rid, exp in exp_by_id.items():
            if rid not in out_by_id:
                continue
            if json.dumps(exp.get("action"), sort_keys=True) == json.dumps(out_by_id[rid].get("action"), sort_keys=True):
                correct += 1
        return correct / total


class RuleDetectionScorer:
    """Precision and recall on rule count detection."""

    def score(self, output: str, expected: dict | None = None, input_text: str = "") -> dict:
        if expected is None:
            return {"rule_detection": None, "error": "no expected output provided"}

        parsed, parse_error = _parse_json(output)
        if parsed is None:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "parse_error": parse_error}

        out_ids = {r.get("rule_id") for r in parsed.get("rules", [])}
        exp_ids = {r.get("rule_id") for r in expected.get("rules", [])}

        true_positives = len(out_ids & exp_ids)
        precision = true_positives / len(out_ids) if out_ids else 0.0
        recall = true_positives / len(exp_ids) if exp_ids else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "expected_count": len(exp_ids),
            "output_count": len(out_ids),
            "true_positives": true_positives,
            "hallucinated_rules": len(out_ids - exp_ids),
            "missed_rules": len(exp_ids - out_ids),
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
        exp_by_id = {r["rule_id"]: r for r in expected.get("rules", [])}

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

            exp_rule = exp_by_id.get(rule.get("rule_id"))
            if exp_rule and rule.get("rule_type") == exp_rule.get("rule_type"):
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
        exp_by_id = {r["rule_id"]: r for r in exp_rules}
        out_by_id = {r.get("rule_id"): r for r in out_rules}

        # Hallucinated rules
        for rid in out_by_id:
            if rid not in exp_by_id:
                failures["hallucinated_rule"] += 1

        # Missing rules
        for rid in exp_by_id:
            if rid not in out_by_id:
                failures["missing_rule"] += 1

        # Per-rule field errors
        for rid, exp_rule in exp_by_id.items():
            out_rule = out_by_id.get(rid)
            if out_rule is None:
                continue

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
