"""Pydantic models for the Redline API."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    pending = "pending"
    parsing = "parsing"
    extracting = "extracting"
    comparing = "comparing"
    complete = "complete"
    error = "error"


class UploadResponse(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.pending
    message: str = "Policy uploaded successfully"


class Condition(BaseModel):
    field: str
    operator: str
    value: str | int | float | bool | list


class Action(BaseModel):
    type: str
    subject: str
    parameters: dict = Field(default_factory=dict)


class ExtractedRule(BaseModel):
    rule_id: str
    rule_type: str
    conditions: list[Condition]
    condition_logic: str
    action: Action
    source_text: str
    confidence: str | None = None


class ExtractionMetadata(BaseModel):
    policy_name: str
    effective_date: str
    applicable_jurisdictions: list[str]


class ExtractionResult(BaseModel):
    job_id: str
    status: JobStatus
    rules: list[ExtractedRule] = Field(default_factory=list)
    metadata: ExtractionMetadata | None = None


class ComparisonDetail(BaseModel):
    parameter: str | None = None
    type: str
    policy_value: str | int | float | None = None
    legislation_value: str | int | float | None = None
    legislation_rule_id: str | None = None
    detail: str


class RuleComparison(BaseModel):
    policy_rule_id: str
    topic: str | None
    conflict_type: str
    jurisdiction: str
    details: list[ComparisonDetail] | str
    legislation_rule_ids: list[str]


class ComparisonResult(BaseModel):
    job_id: str
    status: JobStatus
    comparisons: list[RuleComparison] = Field(default_factory=list)
    missing_requirements: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class LawyerAction(str, Enum):
    approve = "approve"
    deny = "deny"
    edit = "edit"


class RuleReview(BaseModel):
    rule_id: str
    action: LawyerAction
    edited_rule: ExtractedRule | None = None
    notes: str = ""


class ReviewRequest(BaseModel):
    reviews: list[RuleReview]


class ReviewResponse(BaseModel):
    job_id: str
    reviewed_count: int
    message: str


class ReportRuleResult(BaseModel):
    policy_rule_id: str
    topic: str | None
    jurisdiction: str
    conflict_type: str
    details: list[ComparisonDetail] | str
    legislation_rule_ids: list[str]
    lawyer_status: str = "pending"
    lawyer_notes: str = ""


class ComplianceReportResponse(BaseModel):
    report_id: str
    job_id: str
    policy_name: str
    generated_at: str
    rule_results: list[ReportRuleResult]
    missing_requirements: list[dict]
    summary: dict


class RetrainStatus(BaseModel):
    corrections_since_last_retrain: int
    total_corrections: int
    retrain_threshold: int
    last_retrain_at: str | None = None
    last_retrain_error: str | None = None
    retrain_in_progress: bool = False
