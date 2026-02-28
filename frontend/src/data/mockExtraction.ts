import type { ExtractedRule, ReviewedRule, ConflictResult, PolicyMeta } from "@/types";

// ═══════════════════════════════════════════════════════════════════════
// Mock extracted rules from a fictional HR policy
// These deliberately conflict with some CA/Federal legislation to
// demonstrate the comparison engine.
// ═══════════════════════════════════════════════════════════════════════

export const MOCK_POLICY: PolicyMeta = {
    id: "pol_demo_001",
    name: "Acme Corp Employee Handbook 2025",
    filename: "acme_employee_handbook_2025.pdf",
    uploaded_at: new Date().toISOString(),
};

const EXTRACTED: ExtractedRule[] = [
    {
        rule_id: "ext_layoff_001",
        rule_type: "restriction",
        conditions: [
            { field: "employer.employee_count", operator: "gte", value: 50 },
            { field: "action_type", operator: "eq", value: "mass_layoff" },
        ],
        condition_logic: "all",
        action: {
            type: "require",
            subject: "layoff_notice",
            parameters: { notice_days: 30 },
        },
        source_text: "Section 4.2: The Company shall provide at least thirty (30) calendar days advance written notice to all affected employees prior to any mass layoff involving fifty (50) or more employees.",
        confidence: "high",
    },
    {
        rule_id: "ext_final_pay_001",
        rule_type: "entitlement",
        conditions: [
            { field: "employment.status", operator: "eq", value: "terminated" },
        ],
        condition_logic: "all",
        action: {
            type: "require",
            subject: "final_paycheck",
            parameters: { timing: "within_5_business_days" },
        },
        source_text: "Section 6.1: Upon involuntary termination, the employee's final paycheck including all accrued wages and unused PTO shall be issued within five (5) business days.",
        confidence: "high",
    },
    {
        rule_id: "ext_pfl_001",
        rule_type: "leave",
        conditions: [
            { field: "employee.tenure_months", operator: "gte", value: 6 },
            { field: "leave.reason", operator: "in", value: ["bonding", "family_care"] },
        ],
        condition_logic: "all",
        action: {
            type: "grant",
            subject: "paid_family_leave",
            parameters: { weeks: 6, pay_rate: "50%" },
        },
        source_text: "Section 8.3: Employees who have been employed for at least six (6) months are eligible for up to six (6) weeks of paid family leave at fifty percent (50%) of their base salary for bonding with a new child or caring for a seriously ill family member.",
        confidence: "medium",
    },
    {
        rule_id: "ext_overtime_001",
        rule_type: "compensation",
        conditions: [
            { field: "employee.classification", operator: "eq", value: "non_exempt" },
            { field: "hours.weekly", operator: "gt", value: 40 },
        ],
        condition_logic: "all",
        action: {
            type: "require",
            subject: "overtime_pay",
            parameters: { rate: 1.5, basis: "weekly", threshold_hours: 40 },
        },
        source_text: "Section 5.4: Non-exempt employees who work in excess of forty (40) hours in a work week shall be compensated at one and one-half (1.5) times their regular hourly rate for all overtime hours.",
        confidence: "high",
    },
    {
        rule_id: "ext_meal_001",
        rule_type: "entitlement",
        conditions: [
            { field: "hours.daily", operator: "gt", value: 6 },
        ],
        condition_logic: "all",
        action: {
            type: "require",
            subject: "meal_break",
            parameters: { duration_minutes: 30 },
        },
        source_text: "Section 5.7: Employees working more than six (6) hours in a single workday are entitled to one unpaid meal break of at least thirty (30) minutes.",
        confidence: "medium",
    },
    {
        rule_id: "ext_elig_001",
        rule_type: "eligibility",
        conditions: [
            { field: "employee.tenure_months", operator: "gte", value: 3 },
            { field: "employee.status", operator: "eq", value: "full_time" },
        ],
        condition_logic: "all",
        action: {
            type: "grant",
            subject: "health_insurance",
            parameters: { coverage_type: "employer_sponsored" },
        },
        source_text: "Section 7.1: Full-time employees who have completed a three (3) month probationary period are eligible for employer-sponsored health insurance coverage.",
        confidence: "high",
    },
    {
        rule_id: "ext_term_001",
        rule_type: "termination",
        conditions: [
            { field: "performance.rating", operator: "lt", value: 2 },
            { field: "performance.reviews_count", operator: "gte", value: 2 },
        ],
        condition_logic: "all",
        action: {
            type: "require",
            subject: "performance_improvement_plan",
            parameters: { pip_duration_days: 30 },
        },
        source_text: "Section 3.5: An employee who receives two or more performance ratings below 2.0 shall be placed on a Performance Improvement Plan (PIP) of no less than thirty (30) days before any termination action may be initiated.",
        confidence: "low",
    },
    {
        rule_id: "ext_layoff_002",
        rule_type: "restriction",
        conditions: [
            { field: "employee.leave_status", operator: "eq", value: "on_family_leave" },
        ],
        condition_logic: "all",
        action: {
            type: "deny",
            subject: "termination",
        },
        source_text: "Section 4.8: No employee shall be terminated or laid off while on an approved family or medical leave of absence.",
        confidence: "high",
    },
];

// ═══════════════════════════════════════════════════════════════════════
// Pre-computed conflicts — in production, the deterministic comparison
// engine generates these. For the demo, they're hardcoded.
// ═══════════════════════════════════════════════════════════════════════

const CONFLICTS: Record<string, ConflictResult[]> = {
    ext_layoff_001: [
        {
            legislation_name: "California WARN Act",
            jurisdiction: "CA",
            conflict_type: "contradicts",
            explanation: "Policy requires only 30 days notice for 50+ employees. CA WARN Act requires 60 days notice for employers with 75+ employees. The policy's notice period is half the legal requirement.",
            legislation_rule: {
                rule_id: "ca_warn_001",
                rule_type: "restriction",
                conditions: [
                    { field: "employer.employee_count", operator: "gte", value: 75 },
                    { field: "action_type", operator: "eq", value: "mass_layoff" },
                ],
                condition_logic: "all",
                action: { type: "require", subject: "layoff_notice", parameters: { notice_days: 60 } },
                source_text: "Cal. Lab. Code §1401: An employer may not order a mass layoff unless the employer has given 60 days' notice to affected employees.",
            },
        },
        {
            legislation_name: "Federal WARN Act",
            jurisdiction: "federal",
            conflict_type: "contradicts",
            explanation: "Policy requires 30 days for 50+ employees. Federal WARN requires 60 days for 100+ employees. The policy's lower employee threshold is more protective, but the notice period is insufficient.",
            legislation_rule: {
                rule_id: "fed_warn_001",
                rule_type: "restriction",
                conditions: [
                    { field: "employer.employee_count", operator: "gte", value: 100 },
                    { field: "action_type", operator: "eq", value: "mass_layoff" },
                ],
                condition_logic: "all",
                action: { type: "require", subject: "layoff_notice", parameters: { notice_days: 60 } },
                source_text: "29 U.S.C. §2102: An employer shall not order a plant closing or mass layoff until the end of a 60-day period after notice.",
            },
        },
    ],
    ext_final_pay_001: [
        {
            legislation_name: "California Final Paycheck Law",
            jurisdiction: "CA",
            conflict_type: "contradicts",
            explanation: "Policy allows 5 business days to issue final paycheck. California law requires immediate payment on the day of termination. Policy violates Cal. Lab. Code §201.",
            legislation_rule: {
                rule_id: "ca_final_pay_001",
                rule_type: "entitlement",
                conditions: [{ field: "employment.status", operator: "eq", value: "terminated" }],
                condition_logic: "all",
                action: { type: "require", subject: "final_paycheck", parameters: { timing: "immediately" } },
                source_text: "Cal. Lab. Code §201: Wages earned and unpaid at the time of discharge are due and payable immediately.",
            },
        },
        {
            legislation_name: "Federal FLSA — Final Paycheck",
            jurisdiction: "federal",
            conflict_type: "exceeds",
            explanation: "Federal law only requires payment by next regular payday. The policy's 5-day window is stricter than the federal requirement.",
            legislation_rule: {
                rule_id: "fed_final_pay_001",
                rule_type: "entitlement",
                conditions: [{ field: "employment.status", operator: "eq", value: "terminated" }],
                condition_logic: "all",
                action: { type: "require", subject: "final_paycheck", parameters: { timing: "next_regular_payday" } },
                source_text: "Under the FLSA, payment is due by the next regular payday for the pay period in which the termination occurred.",
            },
        },
    ],
    ext_pfl_001: [
        {
            legislation_name: "California Paid Family Leave",
            jurisdiction: "CA",
            conflict_type: "falls_short",
            explanation: "Policy offers 6 weeks at 50% pay. CA PFL provides 8 weeks at 60-70% pay. Policy falls short on both duration and compensation rate.",
            legislation_rule: {
                rule_id: "ca_pfl_001",
                rule_type: "leave",
                conditions: [
                    { field: "employee.sdi_contributions", operator: "eq", value: true },
                    { field: "leave.reason", operator: "in", value: ["bonding", "family_care", "military_assist"] },
                ],
                condition_logic: "all",
                action: { type: "grant", subject: "paid_family_leave", parameters: { weeks: 8, pay_rate: "60-70%" } },
                source_text: "Cal. Unemp. Ins. Code §3301: An individual is eligible for up to eight weeks of PFL benefits at approximately 60 to 70 percent of wages.",
            },
        },
    ],
    ext_overtime_001: [
        {
            legislation_name: "California Overtime Law",
            jurisdiction: "CA",
            conflict_type: "falls_short",
            explanation: "Policy only calculates overtime on a weekly basis (40+ hours). California requires daily overtime after 8 hours. Policy misses the daily OT requirement entirely.",
            legislation_rule: {
                rule_id: "ca_ot_001",
                rule_type: "compensation",
                conditions: [
                    { field: "employee.classification", operator: "eq", value: "non_exempt" },
                    { field: "hours.daily", operator: "gt", value: 8 },
                ],
                condition_logic: "all",
                action: { type: "require", subject: "overtime_pay", parameters: { rate: 1.5, basis: "daily", threshold_hours: 8 } },
                source_text: "Cal. Lab. Code §510: Work in excess of eight hours in one workday shall be compensated at no less than one and one-half times the regular rate.",
            },
        },
        {
            legislation_name: "Federal FLSA — Overtime",
            jurisdiction: "federal",
            conflict_type: "aligned",
            explanation: "Policy matches federal FLSA weekly overtime calculation (40+ hours at 1.5x rate).",
            legislation_rule: {
                rule_id: "fed_ot_001",
                rule_type: "compensation",
                conditions: [
                    { field: "employee.classification", operator: "eq", value: "non_exempt" },
                    { field: "hours.weekly", operator: "gt", value: 40 },
                ],
                condition_logic: "all",
                action: { type: "require", subject: "overtime_pay", parameters: { rate: 1.5, basis: "weekly", threshold_hours: 40 } },
                source_text: "29 U.S.C. §207: No employer shall employ any employee for a workweek longer than forty hours unless compensated at one and one-half times the regular rate.",
            },
        },
    ],
    ext_meal_001: [
        {
            legislation_name: "California Meal Break Law",
            jurisdiction: "CA",
            conflict_type: "falls_short",
            explanation: "Policy triggers meal break after 6 hours. California requires meal break after 5 hours. Employees working between 5 and 6 hours would not receive their legally required break.",
            legislation_rule: {
                rule_id: "ca_meal_001",
                rule_type: "entitlement",
                conditions: [{ field: "hours.daily", operator: "gt", value: 5 }],
                condition_logic: "all",
                action: { type: "require", subject: "meal_break", parameters: { duration_minutes: 30 } },
                source_text: "Cal. Lab. Code §512(a): An employer shall not employ an employee for more than five hours without providing a meal period of not less than 30 minutes.",
            },
        },
        {
            legislation_name: "Federal FLSA — Meal Breaks",
            jurisdiction: "federal",
            conflict_type: "missing",
            explanation: "No federal requirement for meal breaks. The policy exceeds federal requirements by providing any break.",
            legislation_rule: {
                rule_id: "fed_meal_placeholder",
                rule_type: "entitlement",
                conditions: [],
                condition_logic: "all",
                action: { type: "notify", subject: "meal_break" },
                source_text: "The FLSA does not require meal or rest breaks. However, short breaks of 5-20 minutes are considered compensable work hours.",
            },
        },
    ],
    ext_elig_001: [],
    ext_term_001: [],
    ext_layoff_002: [
        {
            legislation_name: "Federal FMLA",
            jurisdiction: "federal",
            conflict_type: "aligned",
            explanation: "Policy prohibits termination during family leave, which aligns with FMLA job protection provisions.",
            legislation_rule: {
                rule_id: "fed_fmla_001",
                rule_type: "leave",
                conditions: [
                    { field: "employee.tenure_months", operator: "gte", value: 12 },
                    { field: "employee.hours_worked", operator: "gte", value: 1250 },
                ],
                condition_logic: "all",
                action: { type: "grant", subject: "family_medical_leave", parameters: { weeks: 12, pay_rate: "unpaid" } },
                source_text: "29 U.S.C. §2614: Any eligible employee who takes leave shall be entitled, on return, to be restored to the position of employment held by the employee.",
            },
        },
    ],
};

// ─── Build the full ReviewedRule list ────────────────────────────────

export function buildMockReviewedRules(): ReviewedRule[] {
    return EXTRACTED.map((rule) => ({
        extracted: rule,
        status: "pending" as const,
        conflicts: CONFLICTS[rule.rule_id] ?? [],
    }));
}
