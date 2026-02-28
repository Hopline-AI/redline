import { useState, useCallback } from "react";
import { RuleCard, sortBySeverity } from "@/components/RuleCard";
import { RuleDetail } from "@/components/RuleDetail";
import { LegislationPanel } from "@/components/LegislationPanel";
import { ReviewActions } from "@/components/ReviewActions";
import { buildMockReviewedRules, MOCK_POLICY } from "@/data/mockExtraction";
import type { ReviewedRule, ReviewStatus } from "@/types";
import { Scale, FileText } from "lucide-react";

export default function Review() {
  const [rules, setRules] = useState<ReviewedRule[]>(() =>
    sortBySeverity(buildMockReviewedRules())
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedRule = rules.find(
    (r) => r.extracted.rule_id === selectedId
  ) ?? null;

  const counts = {
    total: rules.length,
    approved: rules.filter((r) => r.status === "approved").length,
    flagged: rules.filter((r) => r.status === "flagged").length,
    pending: rules.filter((r) => r.status === "pending").length,
  };

  const updateStatus = useCallback(
    (ruleId: string, status: ReviewStatus, notes?: string) => {
      setRules((prev) =>
        prev.map((r) =>
          r.extracted.rule_id === ruleId
            ? { ...r, status, lawyer_notes: notes ?? r.lawyer_notes }
            : r
        )
      );
    },
    []
  );

  return (
    <div className="review-layout">
      {/* Left: Rule list */}
      <div className="rule-list-panel">
        <div className="rule-list-header">
          <div>
            <strong style={{ fontSize: "var(--text-7)" }}>{MOCK_POLICY.name}</strong>
            <br />
            <small className="text-light">
              {counts.total} rules · {counts.approved} approved · {counts.flagged} flagged · {counts.pending} pending
            </small>
          </div>
        </div>

        {rules.map((rule) => (
          <RuleCard
            key={rule.extracted.rule_id}
            rule={rule}
            selected={rule.extracted.rule_id === selectedId}
            onClick={() => setSelectedId(rule.extracted.rule_id)}
          />
        ))}
      </div>

      {/* Right: Detail panel */}
      <div className="detail-panel" style={{ display: "flex", flexDirection: "column" }}>
        {selectedRule ? (
          <>
            <div style={{ flex: 1, overflowY: "auto" }}>
              <RuleDetail rule={selectedRule.extracted} />
              <hr />
              <LegislationPanel conflicts={selectedRule.conflicts} />
            </div>
            <ReviewActions
              currentStatus={selectedRule.status}
              onApprove={(notes) =>
                updateStatus(selectedRule.extracted.rule_id, "approved", notes)
              }
              onFlag={(notes) =>
                updateStatus(selectedRule.extracted.rule_id, "flagged", notes)
              }
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
