import type { ConflictType } from "@/types";

export const CONFLICT_LABELS: Record<ConflictType, string> = {
    contradicts: "Contradicts",
    falls_short: "Falls Short",
    exceeds: "Exceeds",
    missing: "Missing",
    aligned: "Aligned",
};

export const CONFLICT_SEVERITY: Record<ConflictType, number> = {
    contradicts: 0,
    falls_short: 1,
    exceeds: 2,
    missing: 3,
    aligned: 4,
};

export function worstConflict(types: ConflictType[]): ConflictType {
    const severity: ConflictType[] = [
        "contradicts",
        "falls_short",
        "exceeds",
        "missing",
        "aligned",
    ];
    for (const s of severity) {
        if (types.includes(s)) return s;
    }
    return "aligned";
}
