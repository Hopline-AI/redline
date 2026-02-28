import { useParams, useNavigate } from "react-router-dom";
import { RuleCard } from "@/components/RuleCard";
import { RuleDetail } from "@/components/RuleDetail";
import { LegislationPanel } from "@/components/LegislationPanel";
import { ReviewActions } from "@/components/ReviewActions";
import { SEO } from "@/components/SEO";
import { Scale } from "lucide-react";
import { useReviewPage } from "@/hooks/useReviewPage";

export default function Review() {
  const { policyId } = useParams<{ policyId: string }>();
  const navigate = useNavigate();

  const {
    initialData,
    isLoading,
    error,
    selectedId,
    setSelectedId,
    editingId,
    setEditingId,
    filter,
    setFilter,
    counts,
    selectedRule,
    filteredRules,
    updateStatus,
    handleSave,
    saving,
    localRules
  } = useReviewPage(policyId, () => navigate(`/report/${policyId}`));

  const filterOptions = [
    { label: "All Rules", value: "all" as const, count: counts.total },
    { label: "Contradictions", value: "contradicts" as const, count: localRules.filter(r => r.conflicts.some(c => c.conflict_type === "contradicts")).length },
    { label: "Missing", value: "missing" as const, count: localRules.filter(r => r.conflicts.some(c => c.conflict_type === "missing")).length },
    { label: "Pending", value: "pending" as const, count: counts.pending },
    { label: "Aligned", value: "aligned" as const, count: localRules.filter(r => r.conflicts.every(c => c.conflict_type === "aligned") || r.conflicts.length === 0).length },
  ];

  if (isLoading) {
    return <div style={{ padding: 40, textAlign: "center" }}>Loading rules from database...</div>;
  }

  if (error) {
    return <div style={{ padding: 40, color: "var(--danger)" }}>Error: {error.message}</div>;
  }

  return (
    <div className="review-layout">
      <SEO 
        title={`Review: ${initialData?.policyName}`} 
        description={`Conflict analysis for ${initialData?.policyName}. ${counts.total} rules detected.`}
      />
      {/* Left: Rule list */}
      <div className="rule-list-panel">
        <div className="rule-list-header" style={{ flexDirection: "column", alignItems: "stretch", gap: "var(--space-3)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div style={{ flex: 1 }}>
              <h2 style={{ fontSize: "var(--text-6)", margin: 0, fontWeight: "var(--font-bold)", letterSpacing: "-0.01em" }}>{initialData?.policyName}</h2>
              <div className="tabular-nums" style={{ fontSize: "var(--text-8)", color: "var(--muted-foreground)", marginTop: "4px" }}>
                {counts.total} rules · {counts.approved} approved · {counts.rejected} rejected · {counts.pending} pending
              </div>
            </div>
          </div>
          <button 
            className="btn-primary"
            style={{ width: "100%" }}
            disabled={saving || counts.pending === counts.total} 
            onClick={handleSave}
          >
            {saving ? (
              <>
                <div className="spinner" style={{ borderTopColor: "white" }} />
                Saving…
              </>
            ) : "Save & Generate Report"}
          </button>
        </div>

        {/* Filter Bar */}
        <div className="no-scrollbar" style={{ padding: "var(--space-3) var(--space-4)", display: "flex", gap: "var(--space-2)", overflowX: "auto", borderBottom: "1px solid var(--border)", WebkitOverflowScrolling: "touch" }}>
            {filterOptions.map(opt => (
                <button 
                  key={opt.value}
                  onClick={() => setFilter(opt.value)}
                  className={filter === opt.value ? "btn-primary" : "btn-secondary"}
                  style={{ 
                      padding: "4px 12px", 
                      fontSize: "var(--text-8)", 
                      borderRadius: "20px",
                      height: "28px"
                  }}
                >
                    {opt.label}
                    {opt.count !== undefined && (
                        <span className="tabular-nums" style={{ 
                            background: filter === opt.value ? "rgba(255,255,255,0.2)" : "var(--faint)",
                            padding: "0 6px",
                            borderRadius: "10px",
                            fontSize: "10px",
                            marginLeft: "4px"
                        }}>
                            {opt.count}
                        </span>
                    )}
                </button>
            ))}
        </div>

        {filteredRules.map((rule) => (
          <RuleCard
            key={rule.ui_id}
            rule={rule}
            selected={rule.ui_id === selectedId}
            onClick={() => setSelectedId(rule.ui_id)}
          />
        ))}
        {filteredRules.length === 0 && (
          <div style={{ padding: "var(--space-10) var(--space-4)", textAlign: "center", color: "var(--muted-foreground)" }}>
             <p style={{ margin: 0 }}>No rules match this filter.</p>
          </div>
        )}
      </div>

      {/* Right: Detail panel */}
      <div className="detail-panel" style={{ display: "flex", flexDirection: "column", background: "var(--faint)" }}>
        {selectedRule ? (
          <>
            <div style={{ flex: 1, overflowY: "auto", padding: "var(--space-6)", background: "var(--background)", borderRadius: "var(--radius-large)", margin: "var(--space-4)", border: "1px solid var(--border)", boxShadow: "var(--shadow-sm)" }}>
              <RuleDetail
                key={selectedRule.ui_id}
                rule={selectedRule.extracted} 
                isEditing={editingId === selectedRule.ui_id}
                onSave={(edited) => {
                  updateStatus(selectedRule.ui_id, "edited", undefined, edited);
                  setEditingId(null);
                }}
              />
              <hr style={{ margin: "var(--space-6) 0", border: "none", borderTop: "1px solid var(--border)" }} />
              <LegislationPanel conflicts={selectedRule.conflicts} />
            </div>
            <div style={{ padding: "0 var(--space-4) var(--space-4)" }}>
              <ReviewActions
                currentStatus={selectedRule.status}
                isEditing={editingId === selectedRule.ui_id}
                onApprove={(notes) => updateStatus(selectedRule.ui_id, "approved", notes)}
                onReject={(notes) => updateStatus(selectedRule.ui_id, "rejected", notes)}
                onEdit={() => setEditingId(editingId === selectedRule.ui_id ? null : selectedRule.ui_id)}
              />
            </div>
          </>
        ) : (
          <div className="empty-state">
            <Scale size={48} style={{ opacity: 0.2, marginBottom: "var(--space-4)" }} />
            <p>Select a rule from the list to review</p>
            <small className="text-light">
              Rules are sorted by conflict severity — most critical first
            </small>
          </div>
        )}
      </div>
    </div>
  );
}
