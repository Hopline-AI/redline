import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { RuleCard, sortBySeverity } from "@/components/RuleCard";
import { RuleDetail } from "@/components/RuleDetail";
import { LegislationPanel } from "@/components/LegislationPanel";
import { ReviewActions } from "@/components/ReviewActions";
import { getExtraction, getComparison, submitReviews } from "@/api/client";
import type { ReviewedRule, ReviewStatus, ConflictResult, ConflictType } from "@/types";
import { Scale, FileText } from "lucide-react";

export default function Review() {
  const { policyId } = useParams<{ policyId: string }>();
  const navigate = useNavigate();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [localRules, setLocalRules] = useState<ReviewedRule[]>([]);

  const { data: initialData, isLoading, error } = useQuery({
    queryKey: ['reviewData', policyId],
    queryFn: async () => {
        const [extData, cmpData] = await Promise.all([
          getExtraction(policyId!),
          getComparison(policyId!),
        ]);

        const policyName = extData.metadata?.policy_name || "Uploaded Policy";

        const unreviewedRules: ReviewedRule[] = extData.rules.map((rule) => {
          // Find matching comparisons for this rule
          const matches = cmpData.comparisons.filter(c => c.policy_rule_id === rule.rule_id);
          const conflicts = matches.map(c => {
            let type = c.conflict_type;
            if (type === "compliant") type = "aligned";
            if (type === "missing_requirement") type = "missing";

            return {
              conflict_type: type as ConflictType,
              explanation: typeof c.details === "string" ? c.details : c.details?.map((d: any) => d.detail).join("; ") || "No details provided",
              jurisdiction: c.jurisdiction,
              legislation_name: c.topic || c.jurisdiction,
              legislation_rule: {
                rule_id: c.legislation_rule_ids?.[0] || "",
                rule_type: rule.rule_type,
                conditions: [],
                condition_logic: "all",
                action: { type: "notify", subject: "" },
                source_text: "See detailed comparison report"
              }
            } as ConflictResult;
          });

          return {
            ui_id: `${rule.rule_id}-${Math.random().toString(36).substr(2, 9)}`,
            extracted: rule,
            status: "pending",
            conflicts,
          };
        });

        // Add missing requirements as their own reviewable rules
        const missingRules: ReviewedRule[] = (cmpData.missing_requirements || []).map((m: any) => {
          return {
            ui_id: `missing-${m.topic}-${Math.random().toString(36).substr(2, 9)}`,
            extracted: {
              rule_id: `missing_${m.topic}`,
              rule_type: "entitlement", // Fallback rule_type
              conditions: [],
              condition_logic: "all",
              action: { type: "require", subject: m.topic },
              source_text: "MISSING FROM POLICY. See comparison details.",
              confidence: "high"
            },
            status: "pending",
            conflicts: [{
              conflict_type: "missing" as ConflictType,
              explanation: m.details,
              jurisdiction: m.jurisdiction,
              legislation_name: m.legislation_name || m.topic,
              legislation_rule: {
                rule_id: m.legislation_rule_ids?.[0] || "",
                rule_type: "entitlement",
                conditions: [],
                condition_logic: "all",
                action: { type: "require", subject: m.topic },
                source_text: "See detailed legislation."
              }
            }]
          };
        });

        return {
           policyName,
           rules: sortBySeverity([...unreviewedRules, ...missingRules])
        };
    },
    enabled: !!policyId,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
  });

  useEffect(() => {
    if (initialData?.rules) {
      setLocalRules(initialData.rules);
    }
  }, [initialData]);

  const { mutate: saveReviews, isPending: saving } = useMutation({
    mutationFn: async () => {
      if (!policyId) return;
      const reviewed = localRules.filter(r => r.status !== "pending").map(r => ({
        rule_id: r.extracted.rule_id,
        action: r.status === "approved" ? "approve" as const : r.status === "rejected" ? "deny" as const : "edit" as const,
        notes: r.lawyer_notes,
        edited_rule: r.status === "edited" ? r.edited_rule : undefined,
      }));
      await submitReviews(policyId, reviewed);
    },
    onSuccess: () => {
      navigate(`/report/${policyId}`);
    },
    onError: (e: any) => {
      alert("Failed to save reviews: " + e.message);
    }
  });

  const selectedRule = localRules.find(
    (r) => r.ui_id === selectedId
  ) ?? null;

  const counts = {
    total: localRules.length,
    approved: localRules.filter((r) => r.status === "approved").length,
    rejected: localRules.filter((r) => r.status === "rejected").length,
    pending: localRules.filter((r) => r.status === "pending").length,
  };

  const updateStatus = useCallback(
    (uiId: string, status: ReviewStatus, notes?: string, editedRule?: any) => {
      setLocalRules((prev) =>
        prev.map((r) =>
          r.ui_id === uiId
            ? { ...r, status, lawyer_notes: notes ?? r.lawyer_notes, edited_rule: editedRule ?? r.edited_rule }
            : r
        )
      );
    },
    []
  );

  const handleSave = () => {
    saveReviews();
  };

  if (isLoading) {
    return <div style={{ padding: 40, textAlign: "center" }}>Loading rules from database...</div>;
  }

  if (error) {
    return <div style={{ padding: 40, color: "var(--danger)" }}>Error: {error.message}</div>;
  }

  return (
    <div className="review-layout">
      {/* Left: Rule list */}
      <div className="rule-list-panel">
        <div className="rule-list-header">
          <div>
            <strong style={{ fontSize: "var(--text-7)" }}>{initialData?.policyName}</strong>
            <br />
            <small className="text-light">
              {counts.total} rules · {counts.approved} approved · {counts.rejected} rejected · {counts.pending} pending
            </small>
          </div>
          <button 
            disabled={saving || counts.pending === counts.total} 
            onClick={handleSave}
            style={{ padding: "6px 12px" }}
          >
            {saving ? "Saving..." : "Save & Generate Report"}
          </button>
        </div>

        {localRules.map((rule) => (
          <RuleCard
            key={rule.ui_id}
            rule={rule}
            selected={rule.ui_id === selectedId}
            onClick={() => setSelectedId(rule.ui_id)}
          />
        ))}
      </div>

      {/* Right: Detail panel */}
      <div className="detail-panel" style={{ display: "flex", flexDirection: "column" }}>
        {selectedRule ? (
          <>
            <div style={{ flex: 1, overflowY: "auto" }}>
              <RuleDetail
                key={selectedRule.ui_id}
                rule={selectedRule.extracted} 
                isEditing={editingId === selectedRule.ui_id}
                onSave={(edited) => {
                  updateStatus(selectedRule.ui_id, "edited", undefined, edited);
                  setEditingId(null);
                }}
              />
              <hr />
              <LegislationPanel conflicts={selectedRule.conflicts} />
            </div>
            <ReviewActions
              currentStatus={selectedRule.status}
              isEditing={editingId === selectedRule.ui_id}
              onApprove={(notes) => updateStatus(selectedRule.ui_id, "approved", notes)}
              onReject={(notes) => updateStatus(selectedRule.ui_id, "rejected", notes)}
              onEdit={() => setEditingId(editingId === selectedRule.ui_id ? null : selectedRule.ui_id)}
            />
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
