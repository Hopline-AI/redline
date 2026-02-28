import type { ExtractedRule } from "@/types";

const OPERATOR_LABELS: Record<string, string> = {
  eq: "=",
  neq: "≠",
  gt: ">",
  gte: "≥",
  lt: "<",
  lte: "≤",
  in: "∈",
  not_in: "∉",
};

interface Props {
  rule: ExtractedRule;
}

export function RuleDetail({ rule }: Props) {
  return (
    <div>
      {/* Header */}
      <div className="hstack gap-2 mb-4" style={{ flexWrap: "wrap" }}>
        <span className="type-badge">{rule.rule_type}</span>
        <code style={{ fontSize: "var(--text-7)" }}>{rule.rule_id}</code>
        <span className={`confidence-dot ${rule.confidence}`} />
        <small className="text-light">Confidence: {rule.confidence}</small>
      </div>

      {/* Source text */}
      <div className="detail-section">
        <h4>Source Text</h4>
        <blockquote>{rule.source_text}</blockquote>
      </div>

      {/* Conditions */}
      <div className="detail-section">
        <h4>
          Conditions
          <small className="text-light" style={{ marginLeft: "var(--space-2)", textTransform: "none", letterSpacing: "0" }}>
            ({rule.condition_logic === "all" ? "ALL must match" : "ANY can match"})
          </small>
        </h4>
        <ul className="condition-list">
          {rule.conditions.map((c, i) => (
            <li key={i} className="condition-item">
              <span>{c.field}</span>
              <strong>{OPERATOR_LABELS[c.operator] ?? c.operator}</strong>
              <span>{JSON.stringify(c.value)}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Action */}
      <div className="detail-section">
        <h4>Action</h4>
        <div className="action-block">
          <p style={{ margin: 0 }}>
            <strong>{rule.action.type}</strong> → {rule.action.subject}
          </p>
          {rule.action.parameters && (
            <pre style={{ marginTop: "var(--space-2)", fontSize: "var(--text-8)" }}>
              {JSON.stringify(rule.action.parameters, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
