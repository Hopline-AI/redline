import type { Legislation } from "@/types";

// ═══════════════════════════════════════════════════════════════════════
// 5 CA + Federal legislation pairs from the spec
// Each written as a Legislation object matching the JSON schema exactly.
// ═══════════════════════════════════════════════════════════════════════

export const CA_WARN: Legislation = {
    legislation: {
        name: "California WARN Act",
        jurisdiction: "CA",
        effective_date: "2003-01-01",
        source_url: "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?lawCode=LAB&division=2.&title=&part=4.&chapter=4.&article=",
    },
    rules: [
        {
            rule_id: "ca_warn_001",
            rule_type: "restriction",
            conditions: [
                { field: "employer.employee_count", operator: "gte", value: 75 },
                { field: "action_type", operator: "eq", value: "mass_layoff" },
            ],
            condition_logic: "all",
            action: {
                type: "require",
                subject: "layoff_notice",
                parameters: { notice_days: 60 },
            },
            source_text: "Cal. Lab. Code §1401: An employer may not order a mass layoff, relocation, or termination at a covered establishment unless the employer has given 60 days' notice to affected employees.",
        },
    ],
};

export const FEDERAL_WARN: Legislation = {
    legislation: {
        name: "Federal WARN Act",
        jurisdiction: "federal",
        effective_date: "1989-02-04",
        source_url: "https://www.law.cornell.edu/uscode/text/29/chapter-23",
    },
    rules: [
        {
            rule_id: "fed_warn_001",
            rule_type: "restriction",
            conditions: [
                { field: "employer.employee_count", operator: "gte", value: 100 },
                { field: "action_type", operator: "eq", value: "mass_layoff" },
            ],
            condition_logic: "all",
            action: {
                type: "require",
                subject: "layoff_notice",
                parameters: { notice_days: 60 },
            },
            source_text: "29 U.S.C. §2102: An employer shall not order a plant closing or mass layoff until the end of a 60-day period after the employer serves written notice.",
        },
    ],
};

export const CA_FINAL_PAYCHECK: Legislation = {
    legislation: {
        name: "California Final Paycheck Law",
        jurisdiction: "CA",
        effective_date: "2000-01-01",
        source_url: "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=201.&lawCode=LAB",
    },
    rules: [
        {
            rule_id: "ca_final_pay_001",
            rule_type: "entitlement",
            conditions: [
                { field: "employment.status", operator: "eq", value: "terminated" },
            ],
            condition_logic: "all",
            action: {
                type: "require",
                subject: "final_paycheck",
                parameters: { timing: "immediately" },
            },
            source_text: "Cal. Lab. Code §201: If an employer discharges an employee, the wages earned and unpaid at the time of discharge are due and payable immediately.",
        },
    ],
};

export const FEDERAL_FINAL_PAYCHECK: Legislation = {
    legislation: {
        name: "Federal FLSA — Final Paycheck",
        jurisdiction: "federal",
        effective_date: "1938-06-25",
        source_url: "https://www.law.cornell.edu/uscode/text/29/chapter-8",
    },
    rules: [
        {
            rule_id: "fed_final_pay_001",
            rule_type: "entitlement",
            conditions: [
                { field: "employment.status", operator: "eq", value: "terminated" },
            ],
            condition_logic: "all",
            action: {
                type: "require",
                subject: "final_paycheck",
                parameters: { timing: "next_regular_payday" },
            },
            source_text: "Under the FLSA, there is no federal requirement to provide a final paycheck immediately upon termination. Payment is due by the next regular payday for the pay period in which the termination occurred.",
        },
    ],
};

export const CA_PFL: Legislation = {
    legislation: {
        name: "California Paid Family Leave",
        jurisdiction: "CA",
        effective_date: "2004-07-01",
        source_url: "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=3301.&lawCode=UIC",
    },
    rules: [
        {
            rule_id: "ca_pfl_001",
            rule_type: "leave",
            conditions: [
                { field: "employee.sdi_contributions", operator: "eq", value: true },
                { field: "leave.reason", operator: "in", value: ["bonding", "family_care", "military_assist"] },
            ],
            condition_logic: "all",
            action: {
                type: "grant",
                subject: "paid_family_leave",
                parameters: { weeks: 8, pay_rate: "60-70%" },
            },
            source_text: "Cal. Unemp. Ins. Code §3301: An individual is eligible for up to eight weeks of PFL benefits equal to approximately 60 to 70 percent of weekly wages.",
        },
    ],
};

export const FEDERAL_FMLA: Legislation = {
    legislation: {
        name: "Federal FMLA",
        jurisdiction: "federal",
        effective_date: "1993-08-05",
        source_url: "https://www.law.cornell.edu/uscode/text/29/chapter-28",
    },
    rules: [
        {
            rule_id: "fed_fmla_001",
            rule_type: "leave",
            conditions: [
                { field: "employee.tenure_months", operator: "gte", value: 12 },
                { field: "employee.hours_worked", operator: "gte", value: 1250 },
                { field: "employer.employee_count", operator: "gte", value: 50 },
            ],
            condition_logic: "all",
            action: {
                type: "grant",
                subject: "family_medical_leave",
                parameters: { weeks: 12, pay_rate: "unpaid" },
            },
            source_text: "29 U.S.C. §2612: An eligible employee shall be entitled to a total of 12 workweeks of leave during any 12-month period for family and medical reasons. Leave under this section is unpaid.",
        },
    ],
};

export const CA_OVERTIME: Legislation = {
    legislation: {
        name: "California Overtime Law",
        jurisdiction: "CA",
        effective_date: "2000-01-01",
        source_url: "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=510.&lawCode=LAB",
    },
    rules: [
        {
            rule_id: "ca_ot_001",
            rule_type: "compensation",
            conditions: [
                { field: "employee.classification", operator: "eq", value: "non_exempt" },
                { field: "hours.daily", operator: "gt", value: 8 },
            ],
            condition_logic: "all",
            action: {
                type: "require",
                subject: "overtime_pay",
                parameters: { rate: 1.5, basis: "daily", threshold_hours: 8 },
            },
            source_text: "Cal. Lab. Code §510: Any work in excess of eight hours in one workday shall be compensated at the rate of no less than one and one-half times the regular rate of pay.",
        },
    ],
};

export const FEDERAL_OVERTIME: Legislation = {
    legislation: {
        name: "Federal FLSA — Overtime",
        jurisdiction: "federal",
        effective_date: "1938-06-25",
        source_url: "https://www.law.cornell.edu/uscode/text/29/207",
    },
    rules: [
        {
            rule_id: "fed_ot_001",
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
            source_text: "29 U.S.C. §207(a)(1): No employer shall employ any employee for a workweek longer than forty hours unless such employee receives compensation at a rate not less than one and one-half times the regular rate.",
        },
    ],
};

export const CA_MEAL_BREAKS: Legislation = {
    legislation: {
        name: "California Meal Break Law",
        jurisdiction: "CA",
        effective_date: "2000-01-01",
        source_url: "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=512.&lawCode=LAB",
    },
    rules: [
        {
            rule_id: "ca_meal_001",
            rule_type: "entitlement",
            conditions: [
                { field: "hours.daily", operator: "gt", value: 5 },
            ],
            condition_logic: "all",
            action: {
                type: "require",
                subject: "meal_break",
                parameters: { duration_minutes: 30 },
            },
            source_text: "Cal. Lab. Code §512(a): An employer shall not employ an employee for a work period of more than five hours per day without providing the employee with a meal period of not less than 30 minutes.",
        },
    ],
};

// No federal meal break requirement — this is captured as a "missing" conflict
export const FEDERAL_MEAL_BREAKS: Legislation = {
    legislation: {
        name: "Federal FLSA — Meal Breaks",
        jurisdiction: "federal",
        effective_date: "1938-06-25",
        source_url: "https://www.dol.gov/general/topic/workhours/breaks",
    },
    rules: [], // No federal requirement
};

// ─── All legislation for easy access ────────────────────────────────
export const ALL_LEGISLATION: Legislation[] = [
    CA_WARN,
    FEDERAL_WARN,
    CA_FINAL_PAYCHECK,
    FEDERAL_FINAL_PAYCHECK,
    CA_PFL,
    FEDERAL_FMLA,
    CA_OVERTIME,
    FEDERAL_OVERTIME,
    CA_MEAL_BREAKS,
    FEDERAL_MEAL_BREAKS,
];
