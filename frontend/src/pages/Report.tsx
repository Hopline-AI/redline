import { Link, useParams } from "react-router-dom";
import { Download, FileText, ArrowLeft, AlertTriangle } from "lucide-react";
import { ReportSummaryCards } from "@/components/ReportSummaryCards";
import { ReportTable } from "@/components/ReportTable";
import { SEO } from "@/components/SEO";
import { useReportPage } from "@/hooks/useReportPage";

export default function Report() {
  const { policyId } = useParams<{ policyId: string }>();

  const {
    reportData,
    isLoading,
    error,
    rules,
    counts,
    hasPending,
    exportJSON,
    exportPDF
  } = useReportPage(policyId);

  if (isLoading) {
    return <div style={{ padding: 40, textAlign: "center" }}>Loading report...</div>;
  }

  if (error) {
    return <div style={{ padding: 40, color: "var(--danger)" }}>Error: {error.message}</div>;
  }
  
  if (!reportData) return null;

  return (
    <div className="report-page">
      <SEO 
        title={`Compliance Report: ${reportData.policy_name}`} 
        description={`Final compliance report for ${reportData.policy_name}. Produced by Redline Engine.`}
      />
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
