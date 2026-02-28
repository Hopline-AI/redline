import { Condition } from "@/types";

const OPERATOR_LABELS: Record<string, string> = {
    eq: "is exactly",
    neq: "is not",
    gt: "is greater than",
    gte: "is greater than or equal to",
    lt: "is less than",
    lte: "is less than or equal to",
    in: "is one of",
    not_in: "is not one of",
};

export function formatFieldName(field: string): string {
    // Convert "employer.location_state" -> "Employer location state"
    // Convert "employee.hours_worked_daily" -> "Employee hours worked daily"
    const parts = field.split(".");
    const lastPart = parts[parts.length - 1];

    // Replace underscores with spaces and capitalize first letter
    const formatted = lastPart.replace(/_/g, " ");
    return formatted.charAt(0).toUpperCase() + formatted.slice(1);
}

export function formatCondition(condition: Condition): string {
    const fieldName = formatFieldName(condition.field);
    const operatorText = OPERATOR_LABELS[condition.operator] || condition.operator;

    let valueText = String(condition.value);
    if (typeof condition.value === "string") {
        valueText = `"${condition.value}"`;
    } else if (Array.isArray(condition.value)) {
        valueText = `[${condition.value.map(v => typeof v === 'string' ? `"${v}"` : v).join(", ")}]`;
    }

    return `${fieldName} ${operatorText} ${valueText}`;
}
