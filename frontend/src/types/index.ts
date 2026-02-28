// ─── Operator & Action enums ────────────────────────────────────────
export type Operator = "eq" | "neq" | "gt" | "gte" | "lt" | "lte" | "in" | "not_in";
export type ActionType = "grant" | "deny" | "require" | "notify";
export type RuleType = "entitlement" | "restriction" | "eligibility" | "termination" | "leave" | "compensation";
export type ConditionLogic = "all" | "any";
export type Jurisdiction = "CA" | "federal";

// ─── Condition (from legislation schema) ────────────────────────────
export interface Condition {
    field: string;
    operator: Operator;
    value: string | number | boolean | (string | number)[];
}

// ─── Action (from legislation schema) ───────────────────────────────
export interface Action {
    type: ActionType;
    subject: string;
    parameters?: Record<string, unknown>;
}

// ─── Legislation Rule (matches your JSON schema exactly) ────────────
export interface LegislationRule {
    rule_id: string;
    rule_type: RuleType;
    conditions: Condition[];
    condition_logic: ConditionLogic;
    action: Action;
    source_text: string;
}

// ─── Legislation (top-level from schema) ────────────────────────────
export interface Legislation {
    legislation: {
        name: string;
        jurisdiction: Jurisdiction;
        effective_date: string;
        source_url: string;
    };
    rules: LegislationRule[];
}

// ─── Extracted rule from the AI model ───────────────────────────────
export interface ExtractedRule extends LegislationRule {
    confidence: "high" | "medium" | "low";
}

// ─── Comparison result from the deterministic engine ────────────────
export type ConflictType = "contradicts" | "exceeds" | "falls_short" | "missing" | "aligned";

export interface ConflictResult {
    legislation_rule: LegislationRule;
    legislation_name: string;
    jurisdiction: Jurisdiction;
    conflict_type: ConflictType;
    explanation: string;
}

// ─── Frontend review state ──────────────────────────────────────────
export type ReviewStatus = "pending" | "approved" | "rejected" | "edited";

export interface ReviewedRule {
    ui_id: string;
    extracted: ExtractedRule;
    edited_rule?: ExtractedRule;
    status: ReviewStatus;
    lawyer_notes?: string;
    conflicts: ConflictResult[];
}

// ─── Policy metadata ────────────────────────────────────────────────
export interface PolicyMeta {
    id: string;
    name: string;
    filename: string;
    uploaded_at: string;
}

// ─── API response types ─────────────────────────────────────────────
export interface UploadResponse {
    policyId: string;
    filename: string;
}

export type JobPhase = "upload" | "parse" | "extract" | "compare";
export type JobStatus = "queued" | "processing" | "complete" | "error";

export interface JobProgress {
    phase: JobPhase;
    status: JobStatus;
    progress: number; // 0-100
    error?: string;
}
