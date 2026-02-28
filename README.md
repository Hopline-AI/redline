# Redline

Explainable compliance engine for HR policy verification across California and US federal labor rules.

Redline extracts structured decision logic from policy documents using a fine-tuned model, then performs deterministic rule comparison against legislation and produces a lawyer-reviewable report.

## What this repo contains

- `backend/` — Python API, extraction/comparison engine, training and evaluation pipeline.
- `frontend/` — React + Vite review UI for uploads, extracted rules, and compliance reports.
- `video/` — Remotion project for the explainer/demo video.
- `spec.md` — full project specification, architecture, and hackathon plan.

## Monorepo setup

This repository is organized as a polyglot monorepo:

- Root workspace manages Node workspaces: `frontend` and `video`.
- Python backend is managed independently from `backend/pyproject.toml`.

Root scripts are in `package.json`:

- `bun run dev:frontend`
- `bun run dev:video`
- `bun run build:frontend`
- `bun run build:video`
- `bun run lint:frontend`
- `bun run dev:backend`
- `bun run start:backend`

## Architecture (from spec)

1. Policy PDF/text is parsed into plain text and section chunks.
2. Fine-tuned Mistral model extracts structured JSON decision rules.
3. Deterministic comparator checks extracted rules vs CA + federal legislation JSON.
4. Compliance report is generated and served via backend API.
5. Lawyer can approve/deny/edit extractions in the UI.
6. Corrections are logged and fed back into retraining/evaluation loops.

Design principle: AI is only used for extraction; interpretation and compliance checks are deterministic code for auditability.

## Quick start

### Prerequisites

- Node.js 20+
- Bun 1.1+
- Python 3.12+
- `uv` (recommended for backend environment and dependency management)

### 1) Install frontend + video dependencies (workspace)

From repo root:

```bash
bun install
```

### 2) Install backend dependencies

From repo root:

```bash
cd backend
uv sync
```

### 3) Run services

From repo root, start each in a separate terminal:

```bash
bun run dev:frontend
```

```bash
bun run dev:backend
```

Optional demo video editor:

```bash
bun run dev:video
```

## Backend entry points

- API server: `backend/api/server.py`
- One-command startup script (vLLM + API or API-only): `backend/start.sh`
- Comparator logic: `backend/engine/comparator.py`
- Report generation: `backend/engine/report.py`
- Training config/script: `backend/training/config.yaml`, `backend/training/finetune.py`
- Eval scripts: `backend/eval/baseline_eval.py`, `backend/eval/finetuned_eval.py`

## Key data and schema assets

- Extraction schema: `backend/schema/decision_logic.json`
- Legislation schema: `backend/schema/legislation.json`
- Prompt template: `backend/schema/prompt_template.txt`
- Dataset files: `backend/data/train.jsonl`, `backend/data/val.jsonl`, `backend/data/test.jsonl`
- Legislation rules: `backend/engine/legislation/*.json`

## API notes

- FastAPI app: `Redline Compliance Engine`
- Default local API URL: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

## API reference

### Endpoint summary

| Method | Path                | Purpose                                                    | Request Content-Type  | Response Model             |
| ------ | ------------------- | ---------------------------------------------------------- | --------------------- | -------------------------- |
| POST   | `/upload`           | Upload policy text/PDF and start async extraction pipeline | `multipart/form-data` | `UploadResponse`           |
| GET    | `/extract/{job_id}` | Get extracted rules + metadata                             | N/A                   | `ExtractionResult`         |
| GET    | `/compare/{job_id}` | Get compliance comparison results                          | N/A                   | `ComparisonResult`         |
| POST   | `/review/{job_id}`  | Submit lawyer approvals/denials/edits                      | `application/json`    | `ReviewResponse`           |
| GET    | `/report/{job_id}`  | Get final compliance report                                | N/A                   | `ComplianceReportResponse` |
| GET    | `/retrain/status`   | Get auto-retrain pipeline status                           | N/A                   | `RetrainStatus`            |
| GET    | `/health`           | Health + runtime counters                                  | N/A                   | JSON object                |

### Pipeline status values

`pending` → `parsing` → `extracting` → `comparing` → `complete` (or `error`)

### Payload examples

#### 1) Upload policy

Form fields:

- `file` (optional; PDF or text file)
- `text` (optional; plain text policy)
- `policy_name` (optional; default: `Uploaded Policy`)

At least one of `file` or `text` must be provided.

Example cURL (text upload):

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "text=Employees working over 8 hours in a day are eligible for overtime pay." \
  -F "policy_name=Acme Employee Handbook"
```

Example response:

```json
{
  "job_id": "a1b2c3d4",
  "status": "pending",
  "message": "Policy uploaded successfully"
}
```

#### 2) Get extraction

Request:

```bash
curl "http://localhost:8000/extract/a1b2c3d4"
```

Example response:

```json
{
  "job_id": "a1b2c3d4",
  "status": "extracting",
  "rules": [
    {
      "rule_id": "rule_001",
      "rule_type": "compensation",
      "conditions": [
        {
          "field": "employee.hours_worked_day",
          "operator": "gt",
          "value": 8
        }
      ],
      "condition_logic": "all",
      "action": {
        "type": "grant",
        "subject": "overtime_pay",
        "parameters": { "multiplier": 1.5 }
      },
      "source_text": "Employees working over 8 hours in a day are eligible for overtime pay.",
      "confidence": "high"
    }
  ],
  "metadata": {
    "policy_name": "Acme Employee Handbook",
    "effective_date": "2026-02-28",
    "applicable_jurisdictions": ["CA", "federal"]
  }
}
```

#### 3) Get comparison

Request:

```bash
curl "http://localhost:8000/compare/a1b2c3d4"
```

Example response:

```json
{
  "job_id": "a1b2c3d4",
  "status": "comparing",
  "comparisons": [
    {
      "policy_rule_id": "rule_001",
      "topic": "overtime",
      "conflict_type": "falls_short",
      "jurisdiction": "CA",
      "details": [
        {
          "parameter": "daily_threshold_hours",
          "type": "threshold_conflict",
          "policy_value": 10,
          "legislation_value": 8,
          "legislation_rule_id": "ca_overtime_001",
          "detail": "Policy daily threshold is less protective than CA requirement."
        }
      ],
      "legislation_rule_ids": ["ca_overtime_001"]
    }
  ],
  "missing_requirements": [],
  "summary": {
    "total_rules": 1,
    "conflicts": 1,
    "compliant": 0
  }
}
```

#### 4) Submit lawyer review

Request:

```bash
curl -X POST "http://localhost:8000/review/a1b2c3d4" \
  -H "Content-Type: application/json" \
  -d '{
    "reviews": [
      {
        "rule_id": "rule_001",
        "action": "edit",
        "notes": "Threshold should be 8 hours per CA law.",
        "edited_rule": {
          "rule_id": "rule_001",
          "rule_type": "compensation",
          "conditions": [
            {"field": "employee.hours_worked_day", "operator": "gt", "value": 8}
          ],
          "condition_logic": "all",
          "action": {
            "type": "grant",
            "subject": "overtime_pay",
            "parameters": {"multiplier": 1.5}
          },
          "source_text": "Employees working over 8 hours in a day are eligible for overtime pay.",
          "confidence": "high"
        }
      }
    ]
  }'
```

Example response:

```json
{
  "job_id": "a1b2c3d4",
  "reviewed_count": 1,
  "message": "Saved 1 reviews. Corrections logged to W&B for retraining."
}
```

#### 5) Get report

Request:

```bash
curl "http://localhost:8000/report/a1b2c3d4"
```

Example response:

```json
{
  "report_id": "report_a1b2c3d4",
  "job_id": "a1b2c3d4",
  "policy_name": "Acme Employee Handbook",
  "generated_at": "2026-02-28T15:12:00Z",
  "rule_results": [
    {
      "policy_rule_id": "rule_001",
      "topic": "overtime",
      "jurisdiction": "CA",
      "conflict_type": "falls_short",
      "details": [
        {
          "parameter": "daily_threshold_hours",
          "type": "threshold_conflict",
          "policy_value": 10,
          "legislation_value": 8,
          "legislation_rule_id": "ca_overtime_001",
          "detail": "Policy daily threshold is less protective than CA requirement."
        }
      ],
      "legislation_rule_ids": ["ca_overtime_001"],
      "lawyer_status": "edit",
      "lawyer_notes": "Adjusted to CA threshold."
    }
  ],
  "missing_requirements": [],
  "summary": {
    "total_rules": 1,
    "conflicts": 1,
    "compliant": 0
  }
}
```

#### 6) Retrain status

Request:

```bash
curl "http://localhost:8000/retrain/status"
```

Example response:

```json
{
  "corrections_since_last_retrain": 3,
  "total_corrections": 13,
  "retrain_threshold": 10,
  "last_retrain_at": "2026-02-28T14:44:21Z",
  "last_retrain_error": null,
  "retrain_in_progress": false
}
```

#### 7) Health

Request:

```bash
curl "http://localhost:8000/health"
```

Example response:

```json
{
  "status": "ok",
  "jobs_count": 5,
  "lawyer_corrections": 13,
  "weave_enabled": true
}
```

### Error responses

- `400` on `/upload` if both `file` and `text` are missing.
- `404` on `/extract/{job_id}`, `/compare/{job_id}`, `/review/{job_id}`, `/report/{job_id}` when job is unknown.
- `409` on `/report/{job_id}` when report is not generated yet.

## Scope and legal disclaimer

Redline assists with policy extraction and rule comparison. It does not provide legal advice. Final determinations must be reviewed by qualified legal professionals.
