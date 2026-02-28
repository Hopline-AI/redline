"""Pull and analyze metrics from W&B runs.

Two modes:
  1. Direct SDK mode — uses wandb.Api() for standalone execution
  2. MCP mode — outputs GraphQL queries for the W&B MCP Server

Both produce the same MetricsSnapshot dataclass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from self_improve.config import (
    CATEGORY_FLOOR,
    COMPOSITE_WEIGHTS,
    DEFAULT_RESPONSIVENESS,
    FAILURE_MODES,
    RULE_TYPE_METRIC_PREFIX,
    RULE_TYPES,
    TARGET_ACCURACY,
    WANDB_ENTITY,
    WANDB_PROJECT,
)


@dataclass
class MetricsSnapshot:
    """All metrics from a single W&B eval run."""

    run_id: str
    run_name: str
    created_at: str

    # Core metrics
    schema_validity_rate: float = 0.0
    field_accuracy: float = 0.0
    rule_detection_f1: float = 0.0
    source_text_overlap: float = 0.0
    avg_latency_ms: float = 0.0

    # Per-category accuracy
    per_type: dict[str, float] = field(default_factory=dict)

    # Failure mode counts (aggregated across test set)
    failure_modes: dict[str, int] = field(default_factory=dict)

    # Composite score
    composite: float = 0.0

    # Raw summary metrics dict from W&B
    raw: dict[str, Any] = field(default_factory=dict)

    def weakest_category(self) -> tuple[str, float]:
        """Return (category_name, accuracy) of the worst-performing rule type."""
        if not self.per_type:
            return ("unknown", 0.0)
        return min(self.per_type.items(), key=lambda x: x[1])

    def categories_below_floor(self) -> list[tuple[str, float]]:
        """Return categories below CATEGORY_FLOOR, sorted ascending."""
        below = [(k, v) for k, v in self.per_type.items() if v < CATEGORY_FLOOR]
        return sorted(below, key=lambda x: x[1])

    def dominant_failure_mode(self, category: str | None = None) -> str:
        """Return the most frequent failure mode."""
        if not self.failure_modes:
            return "unknown"
        nonzero = {k: v for k, v in self.failure_modes.items() if v > 0}
        if not nonzero:
            return "none"
        return max(nonzero, key=nonzero.get)

    def expected_improvement(self, category: str, responsiveness: float | None = None) -> float:
        """Expected Improvement heuristic for targeting a category.

        EI(cat) = (TARGET_ACCURACY - current) * responsiveness
        Higher EI = more room to improve × more likely to respond to data.
        """
        current = self.per_type.get(category, 0.0)
        gap = max(0.0, TARGET_ACCURACY - current)
        r = responsiveness if responsiveness is not None else DEFAULT_RESPONSIVENESS
        return gap * r


def compute_composite(snapshot: MetricsSnapshot) -> float:
    """Compute the weighted composite score."""
    min_per_type = min(snapshot.per_type.values()) if snapshot.per_type else 0.0

    values = {
        "schema_validity_rate": snapshot.schema_validity_rate,
        "field_accuracy": snapshot.field_accuracy,
        "rule_detection_f1": snapshot.rule_detection_f1,
        "source_text_overlap": snapshot.source_text_overlap,
        "min_per_type_accuracy": min_per_type,
    }

    return sum(COMPOSITE_WEIGHTS[k] * values[k] for k in COMPOSITE_WEIGHTS)


def parse_summary_metrics(run_id: str, run_name: str, created_at: str, summary: dict) -> MetricsSnapshot:
    """Parse a W&B summaryMetrics dict into a MetricsSnapshot."""
    # Handle summaryMetrics being a JSON string (from GraphQL)
    if isinstance(summary, str):
        summary = json.loads(summary)

    def _get(primary: str, fallback: str, default: float = 0.0) -> float:
        v = summary.get(primary)
        return v if v is not None else summary.get(fallback, default)

    schema_validity = _get("eval/schema_validity_rate", "schema_validity_rate")
    field_acc = _get("eval/field_accuracy", "avg_field_accuracy")
    f1 = _get("eval/f1", "avg_f1")
    source_overlap = _get("eval/source_overlap", "avg_source_overlap")
    latency = _get("eval/avg_latency_ms", "avg_latency_ms")

    # Per-type accuracy
    per_type = {}
    for rt in RULE_TYPES:
        val = summary.get(f"{RULE_TYPE_METRIC_PREFIX}{rt}")
        if val is not None:
            per_type[rt] = val
        else:
            # Try alternate keys
            val = summary.get(f"eval/per_type/{rt}", summary.get(f"per_type_{rt}"))
            if val is not None:
                per_type[rt] = val

    # Failure modes
    failure_modes = {}
    for fm in FAILURE_MODES:
        val = summary.get(f"failure_modes/{fm}", summary.get(f"failures/{fm}", 0))
        failure_modes[fm] = val

    snapshot = MetricsSnapshot(
        run_id=run_id,
        run_name=run_name,
        created_at=created_at,
        schema_validity_rate=schema_validity,
        field_accuracy=field_acc,
        rule_detection_f1=f1,
        source_text_overlap=source_overlap,
        avg_latency_ms=latency,
        per_type=per_type,
        failure_modes=failure_modes,
        raw=summary,
    )
    snapshot.composite = compute_composite(snapshot)
    return snapshot


def fetch_latest_run(project: str | None = None, entity: str | None = None) -> MetricsSnapshot:
    """Fetch the latest finished eval run from W&B via the Python SDK."""
    import wandb

    api = wandb.Api()
    entity = entity or WANDB_ENTITY or api.default_entity
    project = project or WANDB_PROJECT

    runs = api.runs(
        f"{entity}/{project}",
        filters={"state": "finished"},
        order="-created_at",
        per_page=1,
    )

    if not runs:
        raise ValueError(f"No finished runs found in {entity}/{project}")

    run = runs[0]
    summary = dict(run.summary)
    return parse_summary_metrics(run.id, run.name, run.created_at, summary)


def fetch_run_by_name(run_name: str, project: str | None = None, entity: str | None = None) -> MetricsSnapshot:
    """Fetch a specific run by display name."""
    import wandb

    api = wandb.Api()
    entity = entity or WANDB_ENTITY or api.default_entity
    project = project or WANDB_PROJECT

    runs = api.runs(
        f"{entity}/{project}",
        filters={"display_name": run_name},
        per_page=1,
    )

    if not runs:
        raise ValueError(f"Run '{run_name}' not found in {entity}/{project}")

    run = runs[0]
    summary = dict(run.summary)
    return parse_summary_metrics(run.id, run.name, run.created_at, summary)


def fetch_run_by_id(run_id: str, project: str | None = None, entity: str | None = None) -> MetricsSnapshot:
    """Fetch a specific run by W&B run ID."""
    import wandb

    api = wandb.Api()
    entity = entity or WANDB_ENTITY or api.default_entity
    project = project or WANDB_PROJECT

    run = api.run(f"{entity}/{project}/{run_id}")
    summary = dict(run.summary)
    return parse_summary_metrics(run.id, run.name, run.created_at, summary)


def fetch_all_eval_runs(project: str | None = None, entity: str | None = None) -> list[MetricsSnapshot]:
    """Fetch all finished eval runs, sorted by creation time (newest first)."""
    import wandb

    api = wandb.Api()
    entity = entity or WANDB_ENTITY or api.default_entity
    project = project or WANDB_PROJECT

    runs = api.runs(
        f"{entity}/{project}",
        filters={"state": "finished"},
        order="-created_at",
        per_page=50,
    )

    snapshots = []
    for run in runs:
        summary = dict(run.summary)
        # Only include runs that have eval metrics
        if any(k.startswith("eval/") or k == "schema_validity_rate" for k in summary):
            snapshots.append(parse_summary_metrics(run.id, run.name, run.created_at, summary))

    return snapshots


def print_snapshot(snapshot: MetricsSnapshot):
    """Pretty-print a metrics snapshot."""
    print(f"\n{'='*60}")
    print(f"Run: {snapshot.run_name} ({snapshot.run_id})")
    print(f"Created: {snapshot.created_at}")
    print(f"{'='*60}")
    print(f"  Composite score:       {snapshot.composite:.4f}")
    print(f"  Schema validity:       {snapshot.schema_validity_rate:.4f}")
    print(f"  Field accuracy:        {snapshot.field_accuracy:.4f}")
    print(f"  Rule detection F1:     {snapshot.rule_detection_f1:.4f}")
    print(f"  Source text overlap:   {snapshot.source_text_overlap:.4f}")
    print(f"  Avg latency (ms):     {snapshot.avg_latency_ms:.1f}")

    if snapshot.per_type:
        print(f"\n  Per-type accuracy:")
        for rt in RULE_TYPES:
            val = snapshot.per_type.get(rt)
            if val is not None:
                marker = " ← WEAK" if val < CATEGORY_FLOOR else ""
                print(f"    {rt:15s}: {val:.4f}{marker}")
        weakest, weakest_val = snapshot.weakest_category()
        print(f"  Weakest: {weakest} ({weakest_val:.4f})")

    if any(v > 0 for v in snapshot.failure_modes.values()):
        print(f"\n  Failure modes:")
        for fm, count in sorted(snapshot.failure_modes.items(), key=lambda x: -x[1]):
            if count > 0:
                print(f"    {fm:20s}: {count}")
        print(f"  Dominant: {snapshot.dominant_failure_mode()}")
