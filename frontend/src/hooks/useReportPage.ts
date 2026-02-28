import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { getReport } from "@/api/client";
import type { ReviewStatus } from "@/types";

export function useReportPage(policyId: string | undefined) {
    const { data: reportData, isLoading, error } = useQuery({
        queryKey: ['report', policyId],
        queryFn: () => {
            if (!policyId) throw new Error("No policy ID provided");
            return getReport(policyId);
        },
        enabled: !!policyId,
    });

    const rules = useMemo(() => {
        if (!reportData) return [];

        const mappedRules = reportData.rule_results.map((r: any) => ({
            rule_id: r.policy_rule_id,
            rule_type: r.topic || "N/A",
            status: r.lawyer_status,
            lawyer_notes: r.lawyer_notes,
            details: r.details, // Details can be a string or Array<{parameter, type, policy_value, legislation_value, detail}>
            conflicts: r.conflict_type !== "aligned" && r.conflict_type !== "compliant" ? [{ conflict_type: r.conflict_type }] : [],
            legislation_ids: r.legislation_rule_ids || []
        }));

        const mappedMissing = (reportData.missing_requirements || []).map((m: any) => ({
            rule_id: `missing-${m.topic}`,
            rule_type: m.topic || "N/A",
            status: "pending",
            lawyer_notes: "",
            details: m.details,
            conflicts: [{ conflict_type: m.conflict_type }],
            legislation_ids: m.legislation_rule_ids || []
        }));

        return [...mappedRules, ...mappedMissing];
    }, [reportData]);

    const counts = useMemo(() => {
        const approved = rules.filter((r) => r.status === "approved").length;
        const rejected = rules.filter((r) => r.status === "rejected").length;
        const edited = rules.filter((r) => r.status === "edit").length;
        const pending = rules.filter((r) => r.status === "pending").length;
        const conflicts = rules.filter((r) =>
            r.conflicts.some((c) => c.conflict_type === "falls_short" || c.conflict_type === "missing_requirement" || c.conflict_type === "contradicts")
        ).length;
        return { approved, rejected, edited, pending, conflicts, total: rules.length };
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

    return {
        reportData,
        isLoading,
        error,
        rules,
        counts,
        hasPending,
        exportJSON,
        exportPDF
    };
}
