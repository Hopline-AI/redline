"""Post-processing: deduplicate extracted rules across chunks."""

from __future__ import annotations

import json
import re


def _rule_fingerprint(rule: dict) -> str:
    """Generate a fingerprint from the rule's semantic identity.

    Two rules are duplicates if they have the same:
      - rule_type
      - action.type + action.subject
      - sorted condition fields + operators
    """
    rule_type = rule.get("rule_type", "")
    action = rule.get("action", {})
    action_key = f"{action.get('type', '')}:{action.get('subject', '')}"

    # Sort conditions by field name for order-independent matching
    conditions = rule.get("conditions", [])
    cond_parts = sorted(
        f"{c.get('field', '')}:{c.get('operator', '')}:{json.dumps(c.get('value', ''), sort_keys=True)}"
        for c in conditions
    )

    return f"{rule_type}|{action_key}|{'&'.join(cond_parts)}"


def deduplicate_rules(rules: list[dict]) -> list[dict]:
    """Remove duplicate rules by semantic fingerprint. Keeps highest confidence."""
    if not rules:
        return rules

    confidence_rank = {"high": 3, "medium": 2, "low": 1}
    seen: dict[str, int] = {}  # fingerprint -> index in unique list
    unique: list[dict] = []

    for rule in rules:
        fp = _rule_fingerprint(rule)
        if fp in seen:
            idx = seen[fp]
            existing_conf = confidence_rank.get(unique[idx].get("confidence", "low"), 1)
            rule_conf = confidence_rank.get(rule.get("confidence", "low"), 1)
            if rule_conf > existing_conf:
                unique[idx] = rule
        else:
            seen[fp] = len(unique)
            unique.append(rule)

    # Fix colliding rule_ids
    seen_ids: set[str] = set()
    for rule in unique:
        rid = rule.get("rule_id", "rule_001")
        if rid in seen_ids:
            base = re.sub(r"_\d+$", "", rid)
            counter = 1
            while f"{base}_{counter:03d}" in seen_ids:
                counter += 1
            rid = f"{base}_{counter:03d}"
            rule["rule_id"] = rid
        seen_ids.add(rid)

    return unique


def post_process(rules: list[dict]) -> list[dict]:
    """Deduplicate rules extracted across multiple chunks."""
    return deduplicate_rules(rules)
