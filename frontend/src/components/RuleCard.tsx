import type { ReviewedRule, ConflictType } from "@/types";
import { ConflictBadge, worstConflict } from "./ConflictBadge";

interface Props {
  rule: ReviewedRule;
  selected: boolean;
  onClick: () => void;
}

export function RuleCard({ rule, selected, onClick }: Props) {
  const { extracted, status, conflicts } = rule;
  const conflictTypes = conflicts.map((c) => c.conflict_type);
  const worst = conflictTypes.length > 0 ? worstConflict(conflictTypes) : null;

  return (
    <div
      className={`rule-card${selected ? " selected" : ""}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
    >
      <div className="rule-card-top">
        <span className="type-badge">{extracted.rule_type}</span>
        {worst && <ConflictBadge type={worst} />}
        <span className={`confidence-dot ${extracted.confidence}`} title={`Confidence: ${extracted.confidence}`} />
        {status !== "pending" && (
          <span className={`status-badge ${status}`}>{status}</span>
        )}
      </div>
      <div className="rule-card-source">{extracted.source_text}</div>
    </div>
  );
}

// ─── Sort helper: most severe conflicts first ───────────────────────
const SEVERITY: Record<ConflictType, number> = {
  contradicts: 0,
  falls_short: 1,
  exceeds: 2,
  missing: 3,
  aligned: 4,
};

export function sortBySeverity(rules: ReviewedRule[]): ReviewedRule[] {
  return [...rules].sort((a, b) => {
    const aWorst = a.conflicts.length
      ? Math.min(...a.conflicts.map((c) => SEVERITY[c.conflict_type]))
      : 5;
    const bWorst = b.conflicts.length
      ? Math.min(...b.conflicts.map((c) => SEVERITY[c.conflict_type]))
      : 5;
    return aWorst - bWorst;
  });
}
