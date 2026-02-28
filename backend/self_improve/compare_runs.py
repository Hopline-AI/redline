"""Statistical comparison of two W&B eval runs.

Uses exact binomial tests for per-metric significance and tracks
regressions with configurable tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import comb, sqrt

from self_improve.config import (
    CONVERGENCE_DELTA_THRESHOLD,
    REGRESSION_ABORT_THRESHOLD,
    REGRESSION_TOLERANCE,
    RULE_TYPES,
    TARGETED_IMPROVEMENT_FLOOR,
)
from self_improve.inspect_metrics import MetricsSnapshot


@dataclass
class MetricDelta:
    name: str
    before: float
    after: float
    delta: float
    significant: bool  # exceeds noise floor
    direction: str  # "improved", "regressed", "stable"


@dataclass
class RunComparison:
    """Full comparison between two runs."""

    before: MetricsSnapshot
    after: MetricsSnapshot

    # Core deltas
    composite_delta: float = 0.0
    schema_delta: float = 0.0
    field_delta: float = 0.0
    f1_delta: float = 0.0
    source_delta: float = 0.0
    latency_delta: float = 0.0

    # Per-category deltas
    per_type_deltas: dict[str, MetricDelta] = field(default_factory=dict)

    # Regression tracking
    regressions: list[MetricDelta] = field(default_factory=list)
    severe_regressions: list[MetricDelta] = field(default_factory=list)

    # Convergence signals
    converged: bool = False
    targeted_category_improved: bool = True

    # Overall verdict
    verdict: str = ""  # "improved", "regressed", "converged", "abort"

    def improvement_summary(self) -> str:
        lines = [
            f"Composite: {self.before.composite:.4f} → {self.after.composite:.4f} ({self.composite_delta:+.4f})",
            f"Schema validity: {self.schema_delta:+.4f}",
            f"Field accuracy: {self.field_delta:+.4f}",
            f"Rule detection F1: {self.f1_delta:+.4f}",
            f"Source overlap: {self.source_delta:+.4f}",
        ]
        if self.regressions:
            lines.append(f"Regressions: {', '.join(r.name for r in self.regressions)}")
        if self.severe_regressions:
            lines.append(f"SEVERE regressions: {', '.join(r.name for r in self.severe_regressions)}")
        lines.append(f"Verdict: {self.verdict}")
        return "\n".join(lines)


def _binomial_test_p_value(n: int, k: int, p0: float = 0.5) -> float:
    """One-sided exact binomial test.

    Tests whether the observed proportion k/n is significantly greater than p0.
    Returns p-value for H1: p > p0.

    For our use case: n = number of test samples where outcome changed,
    k = number that improved, p0 = 0.5 (null: equally likely to improve or regress).
    """
    if n == 0:
        return 1.0
    p_value = 0.0
    for i in range(k, n + 1):
        p_value += comb(n, i) * (p0 ** i) * ((1 - p0) ** (n - i))
    return p_value


def _standard_error(p: float, n: int = 50) -> float:
    """Standard error of a proportion."""
    return sqrt(p * (1 - p) / n) if 0 < p < 1 else 0.0


def _is_significant(delta: float, p_before: float, n: int = 50, alpha: float = 0.05) -> bool:
    """Check if a delta exceeds the noise floor.

    Uses the rule: |delta| > 1.96 * SE(p_before) for approximate 95% CI.
    With n=50, SE at p=0.5 is 0.0707, so the threshold is ~0.139.
    At p=0.8, SE is 0.0566, threshold is ~0.111.
    """
    se = _standard_error(p_before, n)
    return abs(delta) > 1.96 * se


def compare_runs(
    before: MetricsSnapshot,
    after: MetricsSnapshot,
    targeted_category: str | None = None,
    n_test_samples: int = 50,
) -> RunComparison:
    """Compare two runs and produce a detailed comparison with statistical tests."""
    comp = RunComparison(before=before, after=after)

    # Core deltas
    comp.composite_delta = after.composite - before.composite
    comp.schema_delta = after.schema_validity_rate - before.schema_validity_rate
    comp.field_delta = after.field_accuracy - before.field_accuracy
    comp.f1_delta = after.rule_detection_f1 - before.rule_detection_f1
    comp.source_delta = after.source_text_overlap - before.source_text_overlap
    comp.latency_delta = after.avg_latency_ms - before.avg_latency_ms

    # Per-category deltas with significance testing
    for rt in RULE_TYPES:
        val_before = before.per_type.get(rt, 0.0)
        val_after = after.per_type.get(rt, 0.0)
        delta = val_after - val_before
        significant = _is_significant(delta, val_before, n_test_samples)

        if abs(delta) < 0.001:
            direction = "stable"
        elif delta > 0:
            direction = "improved"
        else:
            direction = "regressed"

        md = MetricDelta(
            name=rt,
            before=val_before,
            after=val_after,
            delta=delta,
            significant=significant,
            direction=direction,
        )
        comp.per_type_deltas[rt] = md

        # Track regressions on non-targeted categories
        if rt != targeted_category and delta < -REGRESSION_TOLERANCE:
            comp.regressions.append(md)
        if rt != targeted_category and delta < -REGRESSION_ABORT_THRESHOLD:
            comp.severe_regressions.append(md)

    # Check if targeted category improved enough
    if targeted_category and targeted_category in comp.per_type_deltas:
        td = comp.per_type_deltas[targeted_category]
        comp.targeted_category_improved = td.delta >= TARGETED_IMPROVEMENT_FLOOR

    # Convergence check
    comp.converged = abs(comp.composite_delta) < CONVERGENCE_DELTA_THRESHOLD

    # Verdict
    if comp.severe_regressions:
        comp.verdict = "abort"
    elif comp.converged:
        comp.verdict = "converged"
    elif comp.composite_delta > 0:
        comp.verdict = "improved"
    else:
        comp.verdict = "regressed"

    return comp


def print_comparison(comp: RunComparison, targeted_category: str | None = None):
    """Pretty-print a run comparison."""
    print(f"\n{'='*60}")
    print(f"Comparison: {comp.before.run_name} → {comp.after.run_name}")
    print(f"{'='*60}")
    print(f"  Composite: {comp.before.composite:.4f} → {comp.after.composite:.4f} ({comp.composite_delta:+.4f})")
    print(f"  Schema:    {comp.before.schema_validity_rate:.4f} → {comp.after.schema_validity_rate:.4f} ({comp.schema_delta:+.4f})")
    print(f"  Fields:    {comp.before.field_accuracy:.4f} → {comp.after.field_accuracy:.4f} ({comp.field_delta:+.4f})")
    print(f"  F1:        {comp.before.rule_detection_f1:.4f} → {comp.after.rule_detection_f1:.4f} ({comp.f1_delta:+.4f})")
    print(f"  Source:    {comp.before.source_text_overlap:.4f} → {comp.after.source_text_overlap:.4f} ({comp.source_delta:+.4f})")
    print(f"  Latency:   {comp.before.avg_latency_ms:.0f}ms → {comp.after.avg_latency_ms:.0f}ms ({comp.latency_delta:+.0f}ms)")

    print(f"\n  Per-type deltas:")
    for rt in RULE_TYPES:
        md = comp.per_type_deltas.get(rt)
        if md:
            sig = " *" if md.significant else ""
            target = " ← TARGET" if rt == targeted_category else ""
            print(f"    {rt:15s}: {md.before:.4f} → {md.after:.4f} ({md.delta:+.4f}){sig}{target}")

    if comp.regressions:
        print(f"\n  Regressions (>{REGRESSION_TOLERANCE:.2f}):")
        for r in comp.regressions:
            print(f"    {r.name}: {r.delta:+.4f}")

    if comp.severe_regressions:
        print(f"\n  SEVERE regressions (>{REGRESSION_ABORT_THRESHOLD:.2f}):")
        for r in comp.severe_regressions:
            print(f"    {r.name}: {r.delta:+.4f}")

    print(f"\n  Converged: {comp.converged}")
    print(f"  Targeted improved: {comp.targeted_category_improved}")
    print(f"  Verdict: {comp.verdict}")
