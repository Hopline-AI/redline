import React from 'react';

interface Props {
  counts: {
    total: number;
    approved: number;
    rejected: number;
    pending: number;
    conflicts: number;
  };
}

export function ReportSummaryCards({ counts }: Props) {
  return (
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
        <div className="number" style={{ color: "var(--warning)" }}>{counts.rejected}</div>
        <div className="label">Rejected</div>
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
  );
}
