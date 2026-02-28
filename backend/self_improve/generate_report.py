"""Generate a W&B Report summarizing the self-improvement cycle.

Two modes:
  1. Direct SDK mode — creates report via wandb.Api()
  2. MCP mode — outputs the markdown for create_wandb_report_tool
"""

from __future__ import annotations

from self_improve.compare_runs import RunComparison
from self_improve.config import (
    COMPOSITE_WEIGHTS,
    REPORT_SECTION_CYCLE,
    REPORT_SECTION_OVERVIEW,
    REPORT_TITLE_TEMPLATE,
    RULE_TYPES,
    WANDB_ENTITY,
    WANDB_PROJECT,
)
from self_improve.inspect_metrics import MetricsSnapshot


def _format_per_type_table(snapshots: list[MetricsSnapshot]) -> str:
    """Create a markdown table showing per-type accuracy across all cycles."""
    labels = ["Baseline"] + [f"Cycle {i}" for i in range(1, len(snapshots))]
    header = "| Category | " + " | ".join(labels) + " | Delta |"
    separator = "|" + "---|" * (len(snapshots) + 2)

    rows = []
    for rt in RULE_TYPES:
        values = [s.per_type.get(rt, 0.0) for s in snapshots]
        delta = values[-1] - values[0] if len(values) > 1 else 0.0
        cells = " | ".join(f"{v:.4f}" for v in values)
        rows.append(f"| {rt} | {cells} | {delta:+.4f} |")

    return f"{header}\n{separator}\n" + "\n".join(rows)


def _format_composite_progression(snapshots: list[MetricsSnapshot]) -> str:
    """Show composite score progression."""
    lines = ["| Cycle | Composite | Schema | Fields | F1 | Source | Min Type |"]
    lines.append("|---|---|---|---|---|---|---|")

    for i, s in enumerate(snapshots):
        min_type = min(s.per_type.values()) if s.per_type else 0.0
        lines.append(
            f"| {i} | {s.composite:.4f} | {s.schema_validity_rate:.4f} | "
            f"{s.field_accuracy:.4f} | {s.rule_detection_f1:.4f} | "
            f"{s.source_text_overlap:.4f} | {min_type:.4f} |"
        )

    return "\n".join(lines)


def _format_weight_explanation() -> str:
    """Explain the composite score weights."""
    lines = ["| Metric | Weight | Rationale |"]
    lines.append("|---|---|---|")

    rationales = {
        "schema_validity_rate": "Gating metric — invalid JSON nullifies all downstream metrics",
        "field_accuracy": "Core task quality — correct conditions, operators, actions",
        "rule_detection_f1": "Coverage and precision of rule identification",
        "source_text_overlap": "Faithfulness — extractions must be grounded in policy text",
        "min_per_type_accuracy": "Rawlsian fairness — no category left behind",
    }

    for metric, weight in COMPOSITE_WEIGHTS.items():
        lines.append(f"| {metric} | {weight:.2f} | {rationales.get(metric, '')} |")

    return "\n".join(lines)


def build_report_markdown(
    cycle_snapshots: list[MetricsSnapshot],
    cycle_comparisons: list[RunComparison],
    cycle_metadata: list[dict],
) -> str:
    """Build the full W&B Report markdown content.

    Args:
        cycle_snapshots: MetricsSnapshot for each cycle (index 0 = baseline)
        cycle_comparisons: RunComparison for each cycle transition
        cycle_metadata: list of dicts with keys: target_category, dominant_failure,
                        samples_generated, dataset_version
    """
    n_cycles = len(cycle_comparisons)
    initial = cycle_snapshots[0]
    final = cycle_snapshots[-1]

    sections = []

    # Overview
    sections.append(REPORT_SECTION_OVERVIEW.format(
        project=WANDB_PROJECT,
        n_cycles=n_cycles,
        initial_composite=initial.composite,
        final_composite=final.composite,
        composite_delta=final.composite - initial.composite,
        best_run_name=final.run_name,
    ))

    # Composite weights explanation
    sections.append("## Composite Score Design\n\n" + _format_weight_explanation())

    # Overall progression table
    sections.append("## Metric Progression Across Cycles\n\n" + _format_composite_progression(cycle_snapshots))

    # Per-type accuracy table
    sections.append("## Per-Category Accuracy Progression\n\n" + _format_per_type_table(cycle_snapshots))

    # Per-cycle details
    for i, (comp, meta) in enumerate(zip(cycle_comparisons, cycle_metadata)):
        before = cycle_snapshots[i]
        after = cycle_snapshots[i + 1]

        regressions_str = "None"
        if comp.regressions:
            regressions_str = ", ".join(f"{r.name} ({r.delta:+.4f})" for r in comp.regressions)

        sections.append(REPORT_SECTION_CYCLE.format(
            cycle_num=i + 1,
            target_category=meta.get("target_category", "unknown"),
            target_accuracy_before=before.per_type.get(meta.get("target_category", ""), 0.0),
            dominant_failure=meta.get("dominant_failure", "unknown"),
            samples_generated=meta.get("samples_generated", 0),
            dataset_version=meta.get("dataset_version", i + 1),
            composite_before=before.composite,
            composite_after=after.composite,
            composite_delta=comp.composite_delta,
            schema_before=before.schema_validity_rate,
            schema_after=after.schema_validity_rate,
            schema_delta=comp.schema_delta,
            field_before=before.field_accuracy,
            field_after=after.field_accuracy,
            field_delta=comp.field_delta,
            f1_before=before.rule_detection_f1,
            f1_after=after.rule_detection_f1,
            f1_delta=comp.f1_delta,
            target_accuracy_after=after.per_type.get(meta.get("target_category", ""), 0.0),
            target_delta=getattr(comp.per_type_deltas.get(meta.get("target_category", "")), "delta", 0.0),
            regressions=regressions_str,
        ))

    # Conclusion
    total_delta = final.composite - initial.composite
    conclusion = f"""## Conclusion

After **{n_cycles} improvement cycles**, the composite score improved from **{initial.composite:.4f}** to **{final.composite:.4f}** (+{total_delta:.4f}).

"""

    # Per-category final state
    if final.per_type:
        conclusion += "**Final per-category accuracy:**\n\n"
        for rt in RULE_TYPES:
            val = final.per_type.get(rt, 0.0)
            initial_val = initial.per_type.get(rt, 0.0)
            delta = val - initial_val
            conclusion += f"- `{rt}`: {val:.4f} ({delta:+.4f} from baseline)\n"

    # Stop reason
    if cycle_comparisons:
        last_comp = cycle_comparisons[-1]
        if last_comp.verdict == "converged":
            conclusion += f"\n**Stop reason:** Converged — composite delta ({last_comp.composite_delta:+.4f}) below threshold.\n"
        elif last_comp.verdict == "abort":
            conclusion += f"\n**Stop reason:** Aborted — severe regression detected.\n"
        elif n_cycles >= 5:
            conclusion += f"\n**Stop reason:** Reached maximum cycle count ({n_cycles}).\n"

    sections.append(conclusion)

    return "\n\n---\n\n".join(sections)


def create_wandb_report(
    cycle_snapshots: list[MetricsSnapshot],
    cycle_comparisons: list[RunComparison],
    cycle_metadata: list[dict],
    project: str | None = None,
    entity: str | None = None,
) -> str:
    """Create a W&B Report via wandb-workspaces SDK. Returns the report URL."""
    import wandb_workspaces.reports.v2 as wr

    entity = entity or WANDB_ENTITY
    project = project or WANDB_PROJECT
    n_cycles = len(cycle_comparisons)

    markdown = build_report_markdown(cycle_snapshots, cycle_comparisons, cycle_metadata)
    title = REPORT_TITLE_TEMPLATE.format(n_cycles=n_cycles)

    report = wr.Report(
        entity=entity,
        project=project,
        title=title,
        description="Automated self-improvement loop results",
    )

    report.blocks = [
        wr.TableOfContents(),
        wr.H1(text="Self-Improvement Loop Results"),
        wr.MarkdownBlock(text=markdown),
        wr.H2(text="Training Curves"),
        wr.PanelGrid(
            runsets=[wr.Runset(entity=entity, project=project, name="All Runs")],
            panels=[
                wr.LinePlot(x="Step", y=["train/loss"], title="Training Loss"),
                wr.LinePlot(
                    x="Step",
                    y=[f"eval/per_type/{rt}" for rt in RULE_TYPES],
                    title="Per-Category Accuracy",
                ),
            ],
        ),
        wr.H2(text="Key Metrics"),
        wr.PanelGrid(
            runsets=[wr.Runset(entity=entity, project=project, name="Eval Runs")],
            panels=[
                wr.LinePlot(x="Step", y=["eval/schema_validity_rate"], title="Schema Validity"),
                wr.LinePlot(x="Step", y=["eval/field_accuracy", "eval/f1"], title="Field Accuracy & F1"),
            ],
        ),
    ]

    report.save()
    print(f"\nW&B Report created: {report.url}")
    return report.url


def get_mcp_report_payload(
    cycle_snapshots: list[MetricsSnapshot],
    cycle_comparisons: list[RunComparison],
    cycle_metadata: list[dict],
) -> dict:
    """Return the payload for the W&B MCP create_wandb_report_tool.

    Use this when calling the MCP Server instead of the Python SDK.
    """
    n_cycles = len(cycle_comparisons)
    markdown = build_report_markdown(cycle_snapshots, cycle_comparisons, cycle_metadata)

    return {
        "entity_name": WANDB_ENTITY or "<your-entity>",
        "project_name": WANDB_PROJECT,
        "title": REPORT_TITLE_TEMPLATE.format(n_cycles=n_cycles),
        "description": markdown,
    }
