import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { buildMockReviewedRules, MOCK_POLICY } from "@/data/mockExtraction";
import { ConflictBadge, worstConflict } from "@/components/ConflictBadge";
import type { ReviewedRule } from "@/types";
import { Download, FileText, ArrowLeft, AlertTriangle } from "lucide-react";

export default function Report() {
  // In real app, this would come from shared state/API.
  // For the demo, we use the same mock data.
  const [rules] = useState<ReviewedRule[]>(() => buildMockReviewedRules());

  const counts = useMemo(() => {
    const approved = rules.filter((r) => r.status === "approved").length;
    const flagged = rules.filter((r) => r.status === "flagged").length;
    const pending = rules.filter((r) => r.status === "pending").length;
    const conflicts = rules.filter((r) =>
      r.conflicts.some((c) => c.conflict_type === "contradicts")
    ).length;
    return { approved, flagged, pending, conflicts, total: rules.length };
  }, [rules]);

  const hasPending = counts.pending > 0;

  const exportJSON = () => {
    const approved = rules
      .filter((r) => r.status === "approved")
      .map((r) => r.extracted);
    const blob = new Blob([JSON.stringify(approved, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${MOCK_POLICY.name.replace(/\s+/g, "_")}_approved_rules.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportPDF = () => {
    window.print();
  };

  return (
    <div className="report-page">
      <div className="hstack mb-6">
        <Link to="/review/pol_demo_001" className="hstack gap-1" style={{ textDecoration: "none" }}>
          <ArrowLeft size={16} /> Back to Review
        </Link>
      </div>

      <h1>{MOCK_POLICY.name}</h1>
      <p className="text-light">Compliance Report · {new Date().toLocaleDateString()}</p>

      {/* Summary cards */}
      <div className="report-summary">
        <div className="card summary-card">
          <div className="number">{counts.total}</div>
          <div className="label">Total Rules</div>
        </div>
        <div className="card summary-card">
          <div className="number" style={{ color: "var(--success)" }}>{counts.approved}</div>
          <div className="label">Approved</div>
        </div>
        <div className="card summary-card">
          <div className="number" style={{ color: "var(--warning)" }}>{counts.flagged}</div>
          <div className="label">Flagged</div>
        </div>
        <div className="card summary-card">
          <div className="number" style={{ color: "var(--muted-foreground)" }}>{counts.pending}</div>
          <div className="label">Pending</div>
        </div>
        <div className="card summary-card">
          <div className="number" style={{ color: "var(--danger)" }}>{counts.conflicts}</div>
          <div className="label">Contradictions</div>
        </div>
      </div>

      {/* Export guard */}
      {hasPending && (
        <div role="alert" data-variant="warning" className="mb-4">
          <AlertTriangle size={18} />
          <div>
            <strong>{counts.pending} rules still pending review.</strong>
            <br />
            <small>Review all rules before exporting the final compliance report.</small>
          </div>
        </div>
      )}

      {/* Export buttons */}
      <div className="export-bar">
        <button onClick={exportJSON} disabled={hasPending}>
          <Download size={14} />
          Export JSON
        </button>
        <button data-variant="secondary" onClick={exportPDF}>
          <FileText size={14} />
          Export PDF
        </button>
      </div>

      {/* Rules table */}
      <div className="table">
        <table>
          <thead>
            <tr>
              <th>Rule ID</th>
              <th>Type</th>
              <th>Worst Conflict</th>
              <th>Status</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => {
              const conflictTypes = rule.conflicts.map((c) => c.conflict_type);
              const worst = conflictTypes.length > 0 ? worstConflict(conflictTypes) : null;
              return (
                <tr key={rule.extracted.rule_id}>
                  <td>
                    <code>{rule.extracted.rule_id}</code>
                  </td>
                  <td>
                    <span className="type-badge">{rule.extracted.rule_type}</span>
                  </td>
                  <td>{worst ? <ConflictBadge type={worst} /> : <span className="text-light">—</span>}</td>
                  <td>
                    <span className={`status-badge ${rule.status}`}>{rule.status}</span>
                  </td>
                  <td>
                    <small className="text-light">{rule.lawyer_notes ?? "—"}</small>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
