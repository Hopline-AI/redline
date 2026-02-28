import type { ExtractedRule, Condition, Action, Operator } from "@/types";
import { useParams } from "react-router-dom";
import { Plus, Trash } from "lucide-react";
import { PdfViewerModal } from "./PdfViewerModal";
import { useRuleEditor } from "@/hooks/useRuleEditor";
import { formatCondition } from "@/utils/formatUtils";

const COMMON_FIELDS = [
  "employee.hours_worked_daily",
  "employee.pay_type",
  "employee.employment_type",
  "employer.location_state",
  "employer.employee_count",
  "payroll.pay_frequency"
];

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
    handleAddCondition,
    handleRemoveCondition,
    handleParameterChange,
    handleAddParameter,
    handleRemoveParameter,
    handleSaveClick
  } = useRuleEditor(rule, onSave);
  return (
    <>
      <div>
        {/* Header */}
        <div className="hstack gap-2 mb-4" style={{ flexWrap: "wrap", alignItems: "center" }}>
          <span className="type-badge" style={{ backgroundColor: "var(--faint)", color: "var(--foreground)" }}>{rule.rule_type}</span>
          <code style={{ fontSize: "13px", fontWeight: "600", color: "var(--foreground)" }}>{rule.rule_id}</code>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginLeft: "4px" }}>
            <span className={`confidence-dot ${rule.confidence}`} />
            <span style={{ fontSize: "13px", color: "var(--muted-foreground)" }}>Confidence: {rule.confidence}</span>
          </div>
        </div>

        {/* Source text */}
        <div className="detail-section">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "12px" }}>
            <h4 style={{ margin: 0 }}>Source Text</h4>
            {policyId && (
              <button 
                onClick={() => setShowPdf(true)} 
                className="btn-outline"
                style={{ fontSize: "12px", padding: "4px 8px", borderRadius: "6px" }}
              >
                 View Context in PDF
              </button>
            )}
          </div>
          <blockquote style={{ 
            marginTop: 0, 
            borderLeft: "4px solid var(--border)", 
            paddingLeft: "16px",
            color: "var(--muted-foreground)",
            fontStyle: "italic",
            lineHeight: 1.6
          }}>
            {rule.source_text}
          </blockquote>
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
              <li key={i} className="condition-item" style={{ display: isEditing ? "grid" : "flex", gridTemplateColumns: isEditing ? "1fr auto 1fr auto" : undefined, gap: isEditing ? "12px" : undefined, alignItems: "center" }}>
                {isEditing ? (
                  <>
                    <datalist id="common-fields">
                      {COMMON_FIELDS.map(f => <option key={f} value={f} />)}
                    </datalist>
                    <input 
                      type="text" 
                      list="common-fields"
                      value={c.field} 
                      onChange={(e) => handleConditionChange(i, "field", e.target.value)} 
                      style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "13px", backgroundColor: "var(--background)" }}
                      placeholder="Field name (e.g. employee.pay_type)"
                    />
                    <select 
                      value={c.operator} 
                      onChange={(e) => handleConditionChange(i, "operator", e.target.value)}
                      style={{ width: "auto", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "13px", backgroundColor: "var(--background)", minWidth: "80px" }}
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
                      style={{ width: "100%", padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "13px", backgroundColor: "var(--background)" }}
                      placeholder="Value"
                    />
                    <button 
                      className="btn-ghost" 
                      onClick={() => handleRemoveCondition(i)}
                      style={{ padding: "8px", color: "var(--danger)", borderRadius: "6px" }}
                      title="Remove condition"
                    >
                      <Trash size={14} />
                    </button>
                  </>
                ) : (
                  <span style={{ fontSize: "14px", color: "var(--foreground)" }}>
                    {formatCondition(c)}
                  </span>
                )}
              </li>
            ))}
          </ul>
          {isEditing && (
            <button 
              className="btn-outline" 
              onClick={handleAddCondition}
              style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "12px", padding: "6px 12px", fontSize: "12px", borderRadius: "6px" }}
            >
              <Plus size={14} />
              Add Condition
            </button>
          )}
        </div>

        {/* Action */}
        <div className="detail-section">
          <h4>Action</h4>
          <div className="action-block">
            {isEditing ? (
              <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                <select 
                  value={editedRule.action.type} 
                  onChange={(e) => handleActionChange("type", e.target.value)}
                  style={{ padding: "6px 8px", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "13px", fontWeight: "600", width: "120px", backgroundColor: "var(--background)" }}
                >
                    <option value="grant">grant</option>
                    <option value="deny">deny</option>
                    <option value="require">require</option>
                    <option value="notify">notify</option>
                </select>
                <span style={{ color: "var(--muted-foreground)" }}>→</span>
                <input 
                  type="text" 
                  value={editedRule.action.subject} 
                  onChange={(e) => handleActionChange("subject", e.target.value)}
                  style={{ padding: "6px 8px", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "13px", flex: 1, minWidth: 0, backgroundColor: "var(--background)" }}
                  placeholder="Action subject"
                />
              </div>
            ) : (
              <p style={{ margin: 0, fontSize: "15px" }}>
                <strong style={{ fontWeight: 600 }}>{rule.action.type}</strong> → {rule.action.subject}
              </p>
            )}
            {isEditing && (
              <div style={{ marginTop: "16px" }}>
                <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted-foreground)", textTransform: "uppercase", letterSpacing: "0.05em", display: "block", marginBottom: "8px" }}>Parameters</label>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {Object.entries(editedRule.action.parameters || {}).map(([key, val], idx) => (
                    <div key={idx} style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "10px", alignItems: "center" }}>
                      <input 
                        type="text" 
                        value={key} 
                        onChange={(e) => handleParameterChange(key, e.target.value, val)}
                        style={{ padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "13px", backgroundColor: "var(--background)" }}
                        placeholder="Parameter Name"
                      />
                      <input 
                        type="text" 
                        value={String(val)} 
                        onChange={(e) => {
                          let v: any = e.target.value;
                          if (!isNaN(Number(v)) && v.trim() !== "") v = Number(v);
                          handleParameterChange(key, key, v);
                        }}
                        style={{ padding: "8px 12px", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "13px", backgroundColor: "var(--background)" }}
                        placeholder="Value"
                      />
                      <button 
                        className="btn-ghost" 
                        onClick={() => handleRemoveParameter(key)}
                        style={{ padding: "8px", color: "var(--danger)", borderRadius: "6px" }}
                      >
                        <Trash size={14} />
                      </button>
                    </div>
                  ))}
                  <button 
                    className="btn-outline" 
                    onClick={handleAddParameter}
                    style={{ fontSize: "12px", padding: "6px 12px", width: "fit-content", borderRadius: "6px", display: "flex", alignItems: "center", gap: "4px" }}
                  >
                    <Plus size={14} /> Add Parameter
                  </button>
                </div>
              </div>
            )}
            {!isEditing && rule.action.parameters && Object.keys(rule.action.parameters).length > 0 && (
              <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "4px" }}>
                {Object.entries(rule.action.parameters).map(([k, v]) => (
                  <div key={k} style={{ fontSize: "14px" }}>
                    <span style={{ color: "var(--muted-foreground)" }}>{k.replace(/_/g, " ")}:</span> <span style={{ fontWeight: 500 }}>{String(v)}</span>
                  </div>
                ))}
              </div>
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
