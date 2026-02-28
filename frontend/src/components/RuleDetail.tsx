import type { ExtractedRule, Condition, Action, Operator } from "@/types";
import { useState, useEffect } from "react";

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
  isEditing?: boolean;
  onSave?: (editedRule: ExtractedRule) => void;
}

export function RuleDetail({ rule, isEditing = false, onSave }: Props) {
  const [editedRule, setEditedRule] = useState<ExtractedRule>(rule);

  const handleConditionChange = (index: number, field: keyof Condition, value: any) => {
    const newConditions = [...editedRule.conditions];
    newConditions[index] = { ...newConditions[index], [field]: value };
    setEditedRule({ ...editedRule, conditions: newConditions });
  };

  const handleActionChange = (field: keyof Action, value: any) => {
    setEditedRule({
      ...editedRule,
      action: { ...editedRule.action, [field]: value }
    });
  };

  const handleSaveClick = () => {
    onSave?.(editedRule);
  };
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
            ({editedRule.condition_logic === "all" ? "ALL must match" : "ANY can match"})
          </small>
        </h4>
        <ul className="condition-list">
          {editedRule.conditions.map((c, i) => (
            <li key={i} className="condition-item" style={{ display: isEditing ? "flex" : undefined, gap: isEditing ? "8px" : undefined }}>
              {isEditing ? (
                <>
                  <input 
                    type="text" 
                    value={c.field} 
                    onChange={(e) => handleConditionChange(i, "field", e.target.value)} 
                    style={{ flex: 1, padding: "4px" }}
                  />
                  <select 
                    value={c.operator} 
                    onChange={(e) => handleConditionChange(i, "operator", e.target.value)}
                    style={{ padding: "4px" }}
                  >
                    {Object.entries(OPERATOR_LABELS).map(([op, label]) => (
                      <option key={op} value={op}>{label}</option>
                    ))}
                  </select>
                  <input 
                    type="text" 
                    value={typeof c.value === "object" ? JSON.stringify(c.value) : c.value.toString()} 
                    onChange={(e) => {
                      let val: any = e.target.value;
                      if (!isNaN(Number(val)) && val.trim() !== "") val = Number(val);
                      handleConditionChange(i, "value", val);
                    }} 
                    style={{ flex: 1, padding: "4px" }}
                  />
                </>
              ) : (
                <>
                  <span>{c.field}</span>
                  <strong>{OPERATOR_LABELS[c.operator] ?? c.operator}</strong>
                  <span>{JSON.stringify(c.value)}</span>
                </>
              )}
            </li>
          ))}
        </ul>
      </div>

      {/* Action */}
      <div className="detail-section">
        <h4>Action</h4>
        <div className="action-block">
          {isEditing ? (
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <input 
                type="text" 
                value={editedRule.action.type} 
                onChange={(e) => handleActionChange("type", e.target.value)}
                style={{ padding: "4px", width: "100px" }}
              />
              <span>→</span>
              <input 
                type="text" 
                value={editedRule.action.subject} 
                onChange={(e) => handleActionChange("subject", e.target.value)}
                style={{ padding: "4px", flex: 1 }}
              />
            </div>
          ) : (
            <p style={{ margin: 0 }}>
              <strong>{rule.action.type}</strong> → {rule.action.subject}
            </p>
          )}
          {rule.action.parameters && (
            <pre style={{ marginTop: "var(--space-2)", fontSize: "var(--text-8)" }}>
              {JSON.stringify(rule.action.parameters, null, 2)}
            </pre>
          )}
        </div>
      </div>

      {isEditing && (
        <div style={{ marginTop: "var(--space-4)", display: "flex", justifyContent: "flex-end" }}>
          <button onClick={handleSaveClick}>Save Edits</button>
        </div>
      )}
    </div>
  );
}
