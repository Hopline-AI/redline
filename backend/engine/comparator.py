"""Deterministic comparison engine: extracted policy rules vs legislation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LEGISLATION_DIR = Path(__file__).parent / "legislation"

# Maps topic keywords to canonical topic names
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "layoff_notice": [
        "layoff", "warn", "mass_layoff", "plant_closing", "relocation",
        "layoff_notice", "layoff_notice_to_edd", "layoff_notice_to_government",
    ],
    "final_paycheck": [
        "final_paycheck", "final_pay", "final_wages", "waiting_time_penalty",
        "last_paycheck",
    ],
    "family_leave": [
        "paid_family_leave", "pfl", "fmla", "family_leave", "medical_leave",
        "unpaid_family_medical_leave", "pfl_eligibility", "fmla_employer_coverage",
        "health_benefits_continuation", "bonding_with_new_child",
    ],
    "overtime": [
        "overtime", "overtime_pay", "double_overtime", "weekly_overtime",
        "double_overtime_pay", "seventh_day_double_overtime", "seventh_day_overtime", "weekly_overtime_pay",
    ],
    "meal_breaks": [
        "meal_break", "rest_break", "meal_period", "rest_period",
        "second_meal_break", "meal_break_premium_pay", "short_break_compensation",
        "unpaid_meal_period",
    ],
}

# Legislation file pairs by topic
TOPIC_FILES: dict[str, dict[str, str]] = {
    "layoff_notice": {"CA": "ca_warn.json", "federal": "federal_warn.json"},
    "final_paycheck": {"CA": "ca_final_paycheck.json", "federal": "federal_final_paycheck.json"},
    "family_leave": {"CA": "ca_pfl.json", "federal": "federal_fmla.json"},
    "overtime": {"CA": "ca_overtime.json", "federal": "federal_overtime.json"},
    "meal_breaks": {"CA": "ca_meal_breaks.json", "federal": "federal_meal_breaks.json"},
}

# For numeric parameters, define which direction is "more protective" for the employee
# "higher_is_better" means a higher value benefits the employee
# "lower_is_better" means a lower value benefits the employee
PARAMETER_DIRECTIONS: dict[str, str] = {
    "notice_days": "higher_is_better",
    "max_weeks": "higher_is_better",
    "wage_replacement_rate_min": "higher_is_better",
    "wage_replacement_rate_max": "higher_is_better",
    "rate_multiplier": "higher_is_better",
    "duration_minutes": "higher_is_better",
    "max_days": "higher_is_better",
    "duration_days": "higher_is_better",
}

# Threshold directions for conditions (lower threshold = more protective for employees)
CONDITION_THRESHOLD_FIELDS: dict[str, str] = {
    "employer.employee_count": "lower_is_more_protective",
    "employee.tenure_months": "lower_is_more_protective",
    "employee.hours_worked_last_12_months": "lower_is_more_protective",
}


def load_legislation(legislation_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load all legislation JSON files, indexed by topic and jurisdiction."""
    base = legislation_dir or LEGISLATION_DIR
    result: dict[str, dict[str, Any]] = {}

    for topic, files in TOPIC_FILES.items():
        result[topic] = {}
        for jurisdiction, filename in files.items():
            filepath = base / filename
            if filepath.exists():
                with open(filepath) as f:
                    result[topic][jurisdiction] = json.load(f)

    return result


def classify_topic(rule: dict) -> str | None:
    """Classify a policy rule into a topic based on action.subject and rule_type keywords."""
    subject = rule.get("action", {}).get("subject", "").lower()
    rule_type = rule.get("rule_type", "").lower()
    search_text = f"{subject} {rule_type}"

    # Check for keyword matches
    best_topic = None
    best_score = 0
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in search_text)
        if score > best_score:
            best_score = score
            best_topic = topic

    return best_topic


def _extract_numeric_params(rule: dict) -> dict[str, float]:
    """Extract numeric parameters from a rule's action."""
    params = rule.get("action", {}).get("parameters", {})
    return {k: v for k, v in params.items() if isinstance(v, (int, float))}


def _extract_threshold(rule: dict, field: str) -> float | None:
    """Extract the threshold value for a specific condition field."""
    for cond in rule.get("conditions", []):
        if cond.get("field") == field:
            val = cond.get("value")
            if isinstance(val, (int, float)):
                return val
    return None


def compare_rule(
    policy_rule: dict,
    legislation_rules: list[dict],
    jurisdiction: str,
) -> dict:
    """Compare a single policy rule against matching legislation rules.

    Returns a comparison result dict with conflict_type and details.
    """
    topic = classify_topic(policy_rule)
    if topic is None:
        return {
            "policy_rule_id": policy_rule.get("rule_id"),
            "topic": None,
            "conflict_type": "unclassified",
            "jurisdiction": jurisdiction,
            "details": "Could not classify policy rule into a known topic.",
            "legislation_rule_ids": [],
        }

    # Find legislation rules with matching topic
    matching_leg_rules = []
    for leg_rule in legislation_rules:
        leg_topic = classify_topic(leg_rule)
        if leg_topic == topic:
            matching_leg_rules.append(leg_rule)

    if not matching_leg_rules:
        if jurisdiction == "federal":
            return {
                "policy_rule_id": policy_rule.get("rule_id"),
                "topic": topic,
                "conflict_type": "no_federal_equivalent",
                "jurisdiction": jurisdiction,
                "details": f"No federal legislation found for topic '{topic}'.",
                "legislation_rule_ids": [],
            }
        return {
            "policy_rule_id": policy_rule.get("rule_id"),
            "topic": topic,
            "conflict_type": "no_matching_legislation",
            "jurisdiction": jurisdiction,
            "details": f"No {jurisdiction} legislation found for topic '{topic}'.",
            "legislation_rule_ids": [],
        }

    # Compare parameters
    policy_params = _extract_numeric_params(policy_rule)
    conflicts = []
    leg_rule_ids = [r.get("rule_id") for r in matching_leg_rules]

    for leg_rule in matching_leg_rules:
        leg_params = _extract_numeric_params(leg_rule)

        for param_name, direction in PARAMETER_DIRECTIONS.items():
            policy_val = policy_params.get(param_name)
            leg_val = leg_params.get(param_name)

            if policy_val is None or leg_val is None:
                continue

            if direction == "higher_is_better":
                if policy_val < leg_val:
                    conflicts.append({
                        "parameter": param_name,
                        "type": "falls_short",
                        "policy_value": policy_val,
                        "legislation_value": leg_val,
                        "legislation_rule_id": leg_rule.get("rule_id"),
                        "detail": f"Policy provides {param_name}={policy_val}, legislation requires {leg_val}.",
                    })
                elif policy_val > leg_val:
                    conflicts.append({
                        "parameter": param_name,
                        "type": "exceeds",
                        "policy_value": policy_val,
                        "legislation_value": leg_val,
                        "legislation_rule_id": leg_rule.get("rule_id"),
                        "detail": f"Policy provides {param_name}={policy_val}, exceeds legislation minimum of {leg_val}.",
                    })
            elif direction == "lower_is_better":
                if policy_val > leg_val:
                    conflicts.append({
                        "parameter": param_name,
                        "type": "falls_short",
                        "policy_value": policy_val,
                        "legislation_value": leg_val,
                        "legislation_rule_id": leg_rule.get("rule_id"),
                        "detail": f"Policy sets {param_name}={policy_val}, legislation allows max {leg_val}.",
                    })

        # Compare action types
        policy_action_type = policy_rule.get("action", {}).get("type")
        leg_action_type = leg_rule.get("action", {}).get("type")
        if policy_action_type and leg_action_type and policy_action_type != leg_action_type:
            # e.g., policy says "deny" but legislation says "grant"
            if (policy_action_type == "deny" and leg_action_type in ("grant", "require")) or \
               (policy_action_type == "grant" and leg_action_type == "deny"):
                conflicts.append({
                    "parameter": "action_type",
                    "type": "contradicts",
                    "policy_value": policy_action_type,
                    "legislation_value": leg_action_type,
                    "legislation_rule_id": leg_rule.get("rule_id"),
                    "detail": f"Policy action is '{policy_action_type}' but legislation requires '{leg_action_type}'.",
                })

    # Determine overall conflict type
    if not conflicts:
        conflict_type = "compliant"
    else:
        conflict_types = {c["type"] for c in conflicts}
        if "contradicts" in conflict_types:
            conflict_type = "contradicts"
        elif "falls_short" in conflict_types:
            conflict_type = "falls_short"
        elif "exceeds" in conflict_types:
            conflict_type = "exceeds"
        else:
            conflict_type = "compliant"

    return {
        "policy_rule_id": policy_rule.get("rule_id"),
        "topic": topic,
        "conflict_type": conflict_type,
        "jurisdiction": jurisdiction,
        "details": conflicts if conflicts else "Policy rule is compliant with legislation.",
        "legislation_rule_ids": leg_rule_ids,
    }


def find_missing_requirements(
    policy_rules: list[dict],
    legislation: dict[str, dict[str, Any]],
) -> list[dict]:
    """Find legislation requirements that have no corresponding policy rule."""
    policy_topics = set()
    for rule in policy_rules:
        topic = classify_topic(rule)
        if topic:
            policy_topics.add(topic)

    missing = []
    for topic, jurisdictions in legislation.items():
        if topic not in policy_topics:
            for jurisdiction, leg_data in jurisdictions.items():
                leg_name = leg_data.get("legislation", {}).get("name", topic)
                missing.append({
                    "topic": topic,
                    "jurisdiction": jurisdiction,
                    "conflict_type": "missing_requirement",
                    "legislation_name": leg_name,
                    "details": f"No policy rules found covering '{topic}'. {leg_name} may apply.",
                    "legislation_rule_ids": [r.get("rule_id") for r in leg_data.get("rules", [])],
                })

    return missing


def compare_all(
    policy_rules: list[dict],
    legislation_dir: Path | None = None,
) -> dict:
    """Compare all extracted policy rules against all legislation.

    Returns a dict with per-rule results and missing requirements.
    """
    legislation = load_legislation(legislation_dir)
    results = []

    for policy_rule in policy_rules:
        topic = classify_topic(policy_rule)

        # Compare against both CA and federal legislation
        for jurisdiction in ["CA", "federal"]:
            if topic and topic in legislation and jurisdiction in legislation[topic]:
                leg_data = legislation[topic][jurisdiction]
                leg_rules = leg_data.get("rules", [])
                result = compare_rule(policy_rule, leg_rules, jurisdiction)
                results.append(result)

    missing = find_missing_requirements(policy_rules, legislation)

    # Summary stats
    conflict_counts: dict[str, int] = {}
    for r in results:
        ct = r["conflict_type"]
        conflict_counts[ct] = conflict_counts.get(ct, 0) + 1

    return {
        "comparisons": results,
        "missing_requirements": missing,
        "summary": {
            "total_comparisons": len(results),
            "conflict_counts": conflict_counts,
            "missing_topic_count": len(missing),
        },
    }
