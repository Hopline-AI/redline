"""Generate structured compliance reports from comparison results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.comparator import compare_all


@dataclass
class RuleResult:
    policy_rule_id: str
    topic: str | None
    jurisdiction: str
    conflict_type: str
    details: Any
    legislation_rule_ids: list[str]
    lawyer_status: str = "pending"  # pending | approved | denied | edited
    lawyer_notes: str = ""


@dataclass
class ComplianceReport:
    report_id: str
    policy_name: str
    generated_at: str
    rule_results: list[RuleResult] = field(default_factory=list)
    missing_requirements: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def generate_report(
    policy_name: str,
    policy_rules: list[dict],
    report_id: str | None = None,
    legislation_dir: Path | None = None,
) -> ComplianceReport:
    """Run comparison engine and generate a structured compliance report."""
    comparison = compare_all(policy_rules, legislation_dir)

    rule_results = [
        RuleResult(
            policy_rule_id=r["policy_rule_id"],
            topic=r["topic"],
            jurisdiction=r["jurisdiction"],
            conflict_type=r["conflict_type"],
            details=r["details"],
            legislation_rule_ids=r["legislation_rule_ids"],
        )
        for r in comparison["comparisons"]
    ]

    rid = report_id or f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    return ComplianceReport(
        report_id=rid,
        policy_name=policy_name,
        generated_at=datetime.now(timezone.utc).isoformat(),
        rule_results=rule_results,
        missing_requirements=comparison["missing_requirements"],
        summary=comparison["summary"],
    )


def report_to_dict(report: ComplianceReport) -> dict:
    """Serialize a ComplianceReport to a plain dict."""
    return {
        "report_id": report.report_id,
        "policy_name": report.policy_name,
        "generated_at": report.generated_at,
        "rule_results": [
            {
                "policy_rule_id": r.policy_rule_id,
                "topic": r.topic,
                "jurisdiction": r.jurisdiction,
                "conflict_type": r.conflict_type,
                "details": r.details,
                "legislation_rule_ids": r.legislation_rule_ids,
                "lawyer_status": r.lawyer_status,
                "lawyer_notes": r.lawyer_notes,
            }
            for r in report.rule_results
        ],
        "missing_requirements": report.missing_requirements,
        "summary": report.summary,
    }
