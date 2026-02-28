import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getReport } from "@/api/client";
import type { ReviewStatus } from "@/types";
import { Download, FileText, ArrowLeft, AlertTriangle } from "lucide-react";
import { ReportSummaryCards } from "@/components/ReportSummaryCards";
import { ReportTable } from "@/components/ReportTable";

export default function Report() {
  const { policyId } = useParams<{ policyId: string }>();

  const { data: reportData, isLoading, error } = useQuery({
    queryKey: ['report', policyId],
    queryFn: () => getReport(policyId!),
    enabled: !!policyId,
  });

  const rules = useMemo(() => {
    if (!reportData) return [];
    return reportData.rule_results.map((r: any) => ({
      rule_id: r.policy_rule_id,
      rule_type: "N/A", // If the backend doesn't send this in report, just placeholder
      status: r.lawyer_status as ReviewStatus,
      lawyer_notes: r.lawyer_notes,
      conflicts: r.conflict_type !== "aligned" && r.conflict_type !== "missing" ? [{ conflict_type: r.conflict_type }] : [],
    }));
  }, [reportData]);

  const counts = useMemo(() => {
    const approved = rules.filter((r) => r.status === "approved").length;
    const rejected = rules.filter((r) => r.status === "rejected").length;
    const pending = rules.filter((r) => r.status === "pending").length;
    const conflicts = rules.filter((r) =>
      r.conflicts.some((c) => c.conflict_type === "contradicts")
    ).length;
    return { approved, rejected, pending, conflicts, total: rules.length };
  }, [rules]);

  const hasPending = counts.pending > 0;

  const exportJSON = () => {
    if (!reportData) return;
    const blob = new Blob([JSON.stringify(reportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${reportData.policy_name.replace(/\s+/g, "_")}_compliance_report.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportPDF = () => {
    window.print();
  };

  if (isLoading) {
    return <div style={{ padding: 40, textAlign: "center" }}>Loading report...</div>;
  }

  if (error) {
    return <div style={{ padding: 40, color: "var(--danger)" }}>Error: {error.message}</div>;
  }
  
  if (!reportData) return null;

  return (
    <div className="report-page">
      <div className="hstack mb-6">
        <Link to={`/review/${policyId}`} className="hstack gap-1" style={{ textDecoration: "none" }}>
          <ArrowLeft size={16} /> Back to Review
        </Link>
      </div>

      <h1>{reportData.policy_name}</h1>
      <p className="text-light">Compliance Report · {new Date(reportData.generated_at).toLocaleDateString()}</p>

      {/* Summary cards */}
      <ReportSummaryCards counts={counts} />

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
      <ReportTable rules={rules} />
    </div>
  );
}
