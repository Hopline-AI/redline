import { useState } from "react";
import { z } from "zod";
import type { ExtractedRule, Condition, Action } from "@/types";

export const extractedRuleSchema = z.object({
    rule_id: z.string(),
    rule_type: z.enum(["entitlement", "restriction", "eligibility", "termination", "leave", "compensation"]),
    conditions: z.array(z.object({
        field: z.string().min(1, "Field name is required"),
        operator: z.enum(["eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in"]),
        value: z.union([
            z.string(),
            z.number(),
            z.boolean(),
            z.array(z.union([z.string(), z.number()]))
        ], { required_error: "A valid value is required" })
    })),
    condition_logic: z.enum(["all", "any"]),
    action: z.object({
        type: z.enum(["grant", "deny", "require", "notify"]),
        subject: z.string().min(1, "Subject is required"),
        parameters: z.record(z.unknown()).optional()
    }),
    source_text: z.string(),
    confidence: z.enum(["high", "medium", "low"])
});

export function useRuleEditor(initialRule: ExtractedRule, onSaveCallback?: (rule: ExtractedRule) => void) {
    const [editedRule, setEditedRule] = useState<ExtractedRule>(initialRule);
    const [validationErrors, setValidationErrors] = useState<string[]>([]);
    const [showPdf, setShowPdf] = useState(false);

    const handleConditionChange = (index: number, field: keyof Condition, value: any) => {
        const newConditions = [...editedRule.conditions];
        newConditions[index] = { ...newConditions[index], [field]: value };
        setEditedRule({ ...editedRule, conditions: newConditions });
        setValidationErrors([]);
    };

    const handleActionChange = (field: keyof Action, value: any) => {
        setEditedRule({
            ...editedRule,
            action: { ...editedRule.action, [field]: value }
        });
        setValidationErrors([]);
    };

    const handleAddCondition = () => {
        setEditedRule({
            ...editedRule,
            conditions: [...editedRule.conditions, { field: "", operator: "eq", value: "" }]
        });
        setValidationErrors([]);
    };

    const handleRemoveCondition = (index: number) => {
        const newConditions = editedRule.conditions.filter((_, i) => i !== index);
        setEditedRule({ ...editedRule, conditions: newConditions });
        setValidationErrors([]);
    };

    const handleParameterChange = (oldKey: string, newKey: string, value: any) => {
        const newParams = { ...(editedRule.action.parameters || {}) };
        if (oldKey !== newKey) {
            delete newParams[oldKey];
        }
        newParams[newKey] = value;
        handleActionChange("parameters", newParams);
    };

    const handleAddParameter = () => {
        const newParams = { ...(editedRule.action.parameters || {}), "": "" };
        handleActionChange("parameters", newParams);
    };

    const handleRemoveParameter = (key: string) => {
        const newParams = { ...(editedRule.action.parameters || {}) };
        delete newParams[key];
        handleActionChange("parameters", newParams);
    };

    const handleSaveClick = () => {
        const result = extractedRuleSchema.safeParse(editedRule);

        if (!result.success) {
            const errors = result.error.errors.map(err =>
                `${err.path.join('.')} - ${err.message}`
            );
            setValidationErrors(errors);
            return;
        }

        setValidationErrors([]);
        onSaveCallback?.(editedRule);
    };

    return {
        editedRule,
        validationErrors,
        showPdf,
        setShowPdf,
        handleConditionChange,
        handleActionChange,
        handleAddCondition,
        handleRemoveCondition,
        handleParameterChange,
        handleAddParameter,
        handleRemoveParameter,
        handleSaveClick
    };
}
