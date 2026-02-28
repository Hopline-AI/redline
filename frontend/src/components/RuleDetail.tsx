import type { ExtractedRule, Condition, Action, Operator } from "@/types";
import { useParams } from "react-router-dom";
import { PdfViewerModal } from "./PdfViewerModal";
import { useRuleEditor } from "@/hooks/useRuleEditor";

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
  const { policyId } = useParams<{ policyId: string }>();
  const {
    editedRule,
    validationErrors,
    showPdf,
    setShowPdf,
    handleConditionChange,
    handleActionChange,
    handleSaveClick
  } = useRuleEditor(rule, onSave);
  return (
    <>
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
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "8px" }}>
            <h4 style={{ margin: 0 }}>Source Text</h4>
            {policyId && (
              <button 
                onClick={() => setShowPdf(true)} 
                style={{ fontSize: "12px", padding: "4px 8px", background: "none", border: "1px solid var(--border)", color: "var(--primary)" }}
              >
                 View Context in PDF
              </button>
            )}
          </div>
          <blockquote style={{ marginTop: 0 }}>{rule.source_text}</blockquote>
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
                      placeholder="Field name"
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
                      placeholder="Value"
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
                <select 
                  value={editedRule.action.type} 
                  onChange={(e) => handleActionChange("type", e.target.value)}
                  style={{ padding: "4px", width: "120px" }}
                >
                    <option value="grant">grant</option>
                    <option value="deny">deny</option>
                    <option value="require">require</option>
                    <option value="notify">notify</option>
                </select>
                <span>→</span>
                <input 
                  type="text" 
                  value={editedRule.action.subject} 
                  onChange={(e) => handleActionChange("subject", e.target.value)}
                  style={{ padding: "4px", flex: 1 }}
                  placeholder="Action subject"
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
          <div style={{ marginTop: "var(--space-4)" }}>
              {validationErrors.length > 0 && (
                <div style={{ 
                    color: "var(--danger)", 
                    fontSize: "var(--text-8)", 
                    background: "rgba(220, 38, 38, 0.1)", 
                    padding: "8px", 
                    borderRadius: "4px",
                    marginBottom: "8px" 
                }}>
                  <strong>Validation Errors:</strong>
                  <ul style={{ margin: "4px 0 0 -5px", paddingLeft: "20px" }}>
                    {validationErrors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button onClick={handleSaveClick}>Save Edits</button>
              </div>
          </div>
        )}
      </div>

      {showPdf && policyId && (
         <PdfViewerModal 
            policyId={policyId}
            sourceText={rule.source_text}
            onClose={() => setShowPdf(false)}
         />
      )}
    </>
  );
}
