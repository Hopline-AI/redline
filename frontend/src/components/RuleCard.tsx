import type { ReviewedRule, ConflictType } from "@/types";
import { ConflictBadge } from "./ConflictBadge";
import { worstConflict, CONFLICT_SEVERITY } from "@/utils/conflictUtils";

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
      style={{
        outline: "none",
        borderLeft: selected ? "3px solid var(--primary)" : "3px solid transparent",
        transition: "all var(--transition-fast)"
      }}
    >
      <div className="rule-card-top">
        <span className="type-badge" style={{ fontSize: "10px", padding: "1px 6px" }}>{extracted.rule_type}</span>
        {worst && <ConflictBadge type={worst} />}
        <span className={`confidence-dot ${extracted.confidence}`} title={`Confidence: ${extracted.confidence}`} />
        {status !== "pending" && (
          <span className={`status-badge ${status}`} style={{ fontSize: "10px", padding: "1px 6px" }}>{status}</span>
        )}
      </div>
      <div className="rule-card-source" style={{ 
        display: "-webkit-box",
        WebkitLineClamp: 2,
        WebkitBoxOrient: "vertical",
        overflow: "hidden",
        fontSize: "var(--text-8)",
        lineHeight: "1.5",
        color: selected ? "var(--foreground)" : "var(--muted-foreground)"
      }}>
        {extracted.source_text}
      </div>
    </div>
  );
}

// ─── Sort helper: most severe conflicts first ───────────────────────

export function sortBySeverity(rules: ReviewedRule[]): ReviewedRule[] {
  return [...rules].sort((a, b) => {
    const aWorst = a.conflicts.length
      ? Math.min(...a.conflicts.map((c) => CONFLICT_SEVERITY[c.conflict_type]))
      : 5;
    const bWorst = b.conflicts.length
      ? Math.min(...b.conflicts.map((c) => CONFLICT_SEVERITY[c.conflict_type]))
      : 5;
    return aWorst - bWorst;
  });
}
