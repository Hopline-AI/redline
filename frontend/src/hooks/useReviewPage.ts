import { useState, useCallback, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getExtraction, getComparison, submitReviews } from "@/api/client";
import { sortBySeverity } from "@/components/RuleCard";
import type { ReviewedRule, ReviewStatus, ConflictResult, ConflictType } from "@/types";

export type FilterState = "all" | "contradicts" | "missing" | "aligned" | "exceeds" | "falls_short" | "pending";

export function useReviewPage(policyId: string | undefined, onSaveSuccess: () => void) {
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [localRules, setLocalRules] = useState<ReviewedRule[]>([]);
    const [filter, setFilter] = useState<FilterState>("all");

    const { data: initialData, isLoading, error } = useQuery({
        queryKey: ['reviewData', policyId],
        queryFn: async () => {
            if (!policyId) throw new Error("No policy ID");
            const [extData, cmpData] = await Promise.all([
                getExtraction(policyId),
                getComparison(policyId),
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
        onSuccess: onSaveSuccess,
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

    const handleSave = () => saveReviews();

    const filteredRules = localRules.filter((rule) => {
        if (filter === "all") return true;
        if (filter === "pending") return rule.status === "pending";
        if (filter === "missing") return rule.conflicts.some(c => c.conflict_type === "missing");
        if (filter === "contradicts") return rule.conflicts.some(c => c.conflict_type === "contradicts");
        if (filter === "aligned") return rule.conflicts.every(c => c.conflict_type === "aligned") || rule.conflicts.length === 0;
        return rule.conflicts.some(c => c.conflict_type === filter);
    });

    return {
        initialData,
        isLoading,
        error,
        localRules,
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
        saving
    };
}
