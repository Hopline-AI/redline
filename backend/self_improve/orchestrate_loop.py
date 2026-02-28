"""Autonomous self-improvement loop.

Orchestrates: inspect → diagnose → generate → retrain → evaluate → compare → repeat.

Can run in two modes:
  1. Full autonomous — calls W&B SDK + Claude API + triggers retraining
  2. Step-by-step — prints instructions for each step (for demo / MCP mode)
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from self_improve.compare_runs import RunComparison, compare_runs, print_comparison
from self_improve.config import (
    CONVERGENCE_DELTA_THRESHOLD,
    CONVERGENCE_PATIENCE,
    MAX_CYCLES,
    RULE_TYPES,
    TARGET_ACCURACY,
    TRAIN_JSONL,
    WANDB_ENTITY,
    WANDB_PROJECT,
)
from self_improve.generate_targeted_data import (
    append_to_training_data,
    generate_targeted_samples,
    samples_for_cycle,
)
from self_improve.inspect_metrics import (
    MetricsSnapshot,
    compute_composite,
    fetch_latest_run,
    print_snapshot,
)


@dataclass
class CycleRecord:
    """Record of a single improvement cycle."""

    cycle_num: int
    target_category: str
    dominant_failure: str
    samples_generated: int
    dataset_version: int
    before: MetricsSnapshot
    after: MetricsSnapshot | None = None
    comparison: RunComparison | None = None
    status: str = "pending"  # pending, generating, retraining, evaluating, complete, failed, aborted


@dataclass
class LoopState:
    """Full state of the improvement loop."""

    cycles: list[CycleRecord] = field(default_factory=list)
    snapshots: list[MetricsSnapshot] = field(default_factory=list)
    comparisons: list[RunComparison] = field(default_factory=list)
    consecutive_sub_threshold: int = 0
    stop_reason: str = ""
    started_at: str = ""
    finished_at: str = ""

    # Responsiveness estimates per category (updated after each cycle)
    responsiveness: dict[str, float] = field(default_factory=dict)

    def save(self, path: str = "self_improve/loop_state.json"):
        """Persist loop state to disk for resumability."""
        data = {
            "cycles": [
                {
                    "cycle_num": c.cycle_num,
                    "target_category": c.target_category,
                    "dominant_failure": c.dominant_failure,
                    "samples_generated": c.samples_generated,
                    "dataset_version": c.dataset_version,
                    "status": c.status,
                    "before_run": c.before.run_name if c.before else None,
                    "after_run": c.after.run_name if c.after else None,
                }
                for c in self.cycles
            ],
            "consecutive_sub_threshold": self.consecutive_sub_threshold,
            "stop_reason": self.stop_reason,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "responsiveness": self.responsiveness,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Loop state saved to {path}")


def select_target_category(
    snapshot: MetricsSnapshot,
    state: LoopState,
) -> tuple[str, float]:
    """Select the category to target using Expected Improvement.

    EI(cat) = (TARGET - current) * responsiveness

    Responsiveness is estimated from previous cycles: if targeting 'leave'
    added 30 samples and accuracy went from 0.40 to 0.55, responsiveness
    for 'leave' is (0.55 - 0.40) / (TARGET - 0.40) ≈ 0.29.

    For untargeted categories, use 0.50 as prior.
    """
    best_category = None
    best_ei = -1.0

    for rt in RULE_TYPES:
        current = snapshot.per_type.get(rt, 0.0)
        gap = max(0.0, TARGET_ACCURACY - current)

        # Get responsiveness estimate
        r = state.responsiveness.get(rt, 0.50)

        ei = gap * r
        print(f"    EI({rt:15s}) = ({TARGET_ACCURACY:.2f} - {current:.4f}) * {r:.3f} = {ei:.4f}")

        if ei > best_ei:
            best_ei = ei
            best_category = rt

    return best_category, best_ei


def update_responsiveness(
    state: LoopState,
    category: str,
    accuracy_before: float,
    accuracy_after: float,
):
    """Update the responsiveness estimate for a category after a cycle.

    Uses exponential moving average with alpha=0.6 (recent observations
    weighted more heavily).
    """
    gap = max(0.01, TARGET_ACCURACY - accuracy_before)  # avoid div by 0
    observed_r = (accuracy_after - accuracy_before) / gap

    # Clamp to [0.0, 1.0]
    observed_r = max(0.0, min(1.0, observed_r))

    alpha = 0.6
    old_r = state.responsiveness.get(category, 0.50)
    new_r = alpha * observed_r + (1 - alpha) * old_r
    state.responsiveness[category] = new_r

    print(f"  Responsiveness({category}): {old_r:.3f} → {new_r:.3f} (observed: {observed_r:.3f})")


def run_improvement_loop(
    eval_callback=None,
    retrain_callback=None,
    generate_model: str = "gemini-2.0-flash",
    max_cycles: int | None = None,
    dry_run: bool = False,
):
    """Run the full self-improvement loop.

    Args:
        eval_callback: Function to run evaluation. Takes no args, returns
            a MetricsSnapshot. If None, fetches latest from W&B.
        retrain_callback: Function to trigger retraining. Takes no args.
            If None, prints instructions.
        generate_model: Claude model for data generation.
        max_cycles: Override MAX_CYCLES.
        dry_run: If True, simulate without generating data or retraining.
    """
    max_c = max_cycles or MAX_CYCLES
    state = LoopState()
    state.started_at = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print("REDLINE SELF-IMPROVEMENT LOOP")
    print("=" * 60)

    # Step 1: Get baseline metrics
    print("\n[BASELINE] Fetching initial metrics...")
    if eval_callback:
        baseline = eval_callback()
    else:
        baseline = fetch_latest_run()
    state.snapshots.append(baseline)
    print_snapshot(baseline)

    # Main loop
    for cycle_num in range(1, max_c + 1):
        print(f"\n{'='*60}")
        print(f"CYCLE {cycle_num}/{max_c}")
        print(f"{'='*60}")

        current = state.snapshots[-1]

        # Step 2: Select target category via EI
        print(f"\n[DIAGNOSE] Computing Expected Improvement...")
        target_category, ei = select_target_category(current, state)
        target_accuracy = current.per_type.get(target_category, 0.0)
        dominant_failure = current.dominant_failure_mode(target_category)

        print(f"\n  Selected: {target_category} (accuracy={target_accuracy:.4f}, EI={ei:.4f})")
        print(f"  Dominant failure mode: {dominant_failure}")

        n_samples = samples_for_cycle(cycle_num)

        record = CycleRecord(
            cycle_num=cycle_num,
            target_category=target_category,
            dominant_failure=dominant_failure,
            samples_generated=n_samples,
            dataset_version=cycle_num,
            before=current,
        )

        # Step 3: Generate targeted data
        print(f"\n[GENERATE] Producing {n_samples} targeted samples...")
        record.status = "generating"

        if dry_run:
            print(f"  DRY RUN — skipping generation")
            new_samples = []
        else:
            new_samples = generate_targeted_samples(
                target_category=target_category,
                dominant_failure=dominant_failure,
                cycle_num=cycle_num,
                model=generate_model,
                seed=42 + cycle_num,
            )

        record.samples_generated = len(new_samples)

        if new_samples:
            total = append_to_training_data(new_samples)
            print(f"  Training set size: {total}")
        elif not dry_run:
            print("  WARNING: No valid samples generated. Skipping cycle.")
            record.status = "failed"
            state.cycles.append(record)
            continue

        # Step 4: Retrain
        print(f"\n[RETRAIN] Triggering retraining...")
        record.status = "retraining"

        if retrain_callback:
            retrain_callback()
        else:
            print("  No retrain_callback provided.")
            print("  To retrain manually:")
            print("    python training/finetune.py --config training/config.yaml")
            print("  Or trigger via HF Jobs:")
            print("    python jobs/run_job.py run jobs/retrain.yaml")
            if not dry_run:
                print("\n  Waiting for retrain to complete...")
                print("  (In production, poll W&B for a new finished run)")

        # Step 5: Evaluate
        print(f"\n[EVALUATE] Running evaluation...")
        record.status = "evaluating"

        if eval_callback:
            new_snapshot = eval_callback()
        elif dry_run:
            # Build a fresh snapshot instead of deepcopy (W&B raw dict is not copyable)
            new_snapshot = MetricsSnapshot(
                run_id=f"sim_{cycle_num}",
                run_name=f"cycle_{cycle_num}_simulated",
                created_at=current.created_at,
                schema_validity_rate=current.schema_validity_rate,
                field_accuracy=current.field_accuracy,
                rule_detection_f1=current.rule_detection_f1,
                source_text_overlap=current.source_text_overlap,
                avg_latency_ms=current.avg_latency_ms,
                per_type=dict(current.per_type),
                failure_modes=dict(current.failure_modes),
            )
            # Simulate: targeted category improves by ~0.08, others stay stable
            if target_category in new_snapshot.per_type:
                new_snapshot.per_type[target_category] = min(
                    0.95, new_snapshot.per_type[target_category] + 0.08
                )
            new_snapshot.composite = compute_composite(new_snapshot)
        else:
            # Poll W&B for a new finished run (different from the current one)
            print("  Polling W&B for new eval run...")
            poll_interval = 30
            max_polls = 60  # 30 minutes max
            for poll in range(max_polls):
                time.sleep(poll_interval)
                new_snapshot = fetch_latest_run()
                if new_snapshot.run_id != current.run_id:
                    break
                print(f"    Waiting for new run... ({poll + 1}/{max_polls})")
            else:
                print("  WARNING: No new run appeared. Using latest available.")
                new_snapshot = fetch_latest_run()

        state.snapshots.append(new_snapshot)
        print_snapshot(new_snapshot)

        # Step 6: Compare
        print(f"\n[COMPARE] Analyzing improvement...")
        comparison = compare_runs(current, new_snapshot, targeted_category=target_category)
        state.comparisons.append(comparison)
        print_comparison(comparison, targeted_category=target_category)

        record.after = new_snapshot
        record.comparison = comparison

        # Update responsiveness estimate
        accuracy_before = current.per_type.get(target_category, 0.0)
        accuracy_after = new_snapshot.per_type.get(target_category, 0.0)
        update_responsiveness(state, target_category, accuracy_before, accuracy_after)

        record.status = "complete"
        state.cycles.append(record)
        state.save()

        # Step 7: Check stopping criteria
        if comparison.verdict == "abort":
            state.stop_reason = f"Aborted: severe regression in cycle {cycle_num}"
            print(f"\n  ABORT: Severe regression detected. Stopping loop.")
            break

        if comparison.converged:
            state.consecutive_sub_threshold += 1
            print(f"  Sub-threshold cycle ({state.consecutive_sub_threshold}/{CONVERGENCE_PATIENCE})")
            if state.consecutive_sub_threshold >= CONVERGENCE_PATIENCE:
                state.stop_reason = f"Converged after {cycle_num} cycles (patience={CONVERGENCE_PATIENCE})"
                print(f"\n  CONVERGED: {CONVERGENCE_PATIENCE} consecutive sub-threshold cycles. Stopping.")
                break
        else:
            state.consecutive_sub_threshold = 0

        if not comparison.targeted_category_improved:
            print(f"  WARNING: Targeted category '{target_category}' did not improve enough.")

    else:
        state.stop_reason = f"Reached maximum cycles ({max_c})"
        print(f"\n  Reached maximum cycles ({max_c}). Stopping.")

    state.finished_at = datetime.now(timezone.utc).isoformat()
    state.save()

    # Step 8: Generate report
    print(f"\n{'='*60}")
    print("GENERATING REPORT")
    print(f"{'='*60}")

    cycle_metadata = [
        {
            "target_category": c.target_category,
            "dominant_failure": c.dominant_failure,
            "samples_generated": c.samples_generated,
            "dataset_version": c.dataset_version,
        }
        for c in state.cycles
        if c.status == "complete"
    ]

    completed_comparisons = state.comparisons

    from self_improve.generate_report import build_report_markdown, get_mcp_report_payload

    markdown = build_report_markdown(state.snapshots, completed_comparisons, cycle_metadata)

    # Save markdown locally
    report_path = Path("self_improve/improvement_report.md")
    report_path.write_text(markdown)
    print(f"  Report saved to {report_path}")

    # Print MCP payload for creating W&B Report
    payload = get_mcp_report_payload(state.snapshots, completed_comparisons, cycle_metadata)
    print(f"\n  To create W&B Report via MCP, use create_wandb_report_tool with:")
    print(f"    entity_name: {payload['entity_name']}")
    print(f"    project_name: {payload['project_name']}")
    print(f"    title: {payload['title']}")

    # Try creating via SDK
    try:
        from self_improve.generate_report import create_wandb_report
        url = create_wandb_report(state.snapshots, completed_comparisons, cycle_metadata)
        print(f"\n  W&B Report URL: {url}")
    except Exception as e:
        print(f"\n  Could not create W&B Report via SDK: {e}")
        print("  Use the MCP payload above to create it manually.")

    # Final summary
    initial = state.snapshots[0]
    final = state.snapshots[-1]
    print(f"\n{'='*60}")
    print("LOOP COMPLETE")
    print(f"{'='*60}")
    print(f"  Cycles: {len(state.cycles)}")
    print(f"  Composite: {initial.composite:.4f} → {final.composite:.4f} ({final.composite - initial.composite:+.4f})")
    print(f"  Stop reason: {state.stop_reason}")
    print(f"  Duration: {state.started_at} → {state.finished_at}")

    return state


def main():
    parser = argparse.ArgumentParser(description="Run Redline self-improvement loop")
    parser.add_argument("--max-cycles", type=int, default=MAX_CYCLES, help="Maximum improvement cycles")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without generating data or retraining")
    parser.add_argument("--generate-model", default="gemini-2.0-flash", help="Gemini model for data generation")
    parser.add_argument("--no-callbacks", action="store_true", help="Run without HF Jobs callbacks (print instructions instead)")
    args = parser.parse_args()

    eval_cb = None
    retrain_cb = None

    if not args.no_callbacks and not args.dry_run:
        from self_improve.callbacks import eval_callback, retrain_callback
        eval_cb = eval_callback
        retrain_cb = retrain_callback

    run_improvement_loop(
        eval_callback=eval_cb,
        retrain_callback=retrain_cb,
        max_cycles=args.max_cycles,
        dry_run=args.dry_run,
        generate_model=args.generate_model,
    )


if __name__ == "__main__":
    main()
