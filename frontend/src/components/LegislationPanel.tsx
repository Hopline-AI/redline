import type { ConflictResult } from "@/types";
import { ConflictBadge } from "./ConflictBadge";
import { ExternalLink } from "lucide-react";

interface Props {
  conflicts: ConflictResult[];
}

export function LegislationPanel({ conflicts }: Props) {
  if (conflicts.length === 0) {
    return (
      <div className="detail-section">
        <h4>Legislation Comparison</h4>
        <p className="text-light" style={{ fontSize: "var(--text-7)" }}>
          No matching legislation found for this rule.
        </p>
      </div>
    );
  }

  return (
    <div className="detail-section">
      <h4>Legislation Comparison</h4>
      {conflicts.map((c, i) => (
        <div key={i} className="legislation-match">
          <div className="legislation-match-header">
            <strong style={{ fontSize: "var(--text-7)" }}>{c.legislation_name}</strong>
            <span className="jurisdiction-badge">{c.jurisdiction}</span>
            <ConflictBadge type={c.conflict_type} />
          </div>

          <p style={{ fontSize: "var(--text-7)", marginBottom: "var(--space-3)" }}>
            {c.explanation}
          </p>

          <blockquote style={{ fontSize: "var(--text-8)" }}>
            {c.legislation_rule.source_text}
          </blockquote>

          {/* Collapsible legislation conditions detail */}
          {c.legislation_rule.conditions.length > 0 && (
            <details style={{ marginTop: "var(--space-2)" }}>
              <summary>View legislation rule details</summary>
              <div style={{ padding: "var(--space-3)" }}>
                <p style={{ fontSize: "var(--text-8)", marginBottom: "var(--space-2)" }}>
                  <strong>Action:</strong> {c.legislation_rule.action.type} → {c.legislation_rule.action.subject}
                </p>
                {c.legislation_rule.action.parameters && (
                  <pre style={{ fontSize: "var(--text-8)" }}>
                    {JSON.stringify(c.legislation_rule.action.parameters, null, 2)}
                  </pre>
                )}
              </div>
            </details>
          )}
        </div>
      ))}
    </div>
  );
}
