# Redline — Explainable Compliance Engine

## Problem

Companies operating in California must verify internal HR/employee policies against both California state and federal legislation. This currently requires 2+ lawyers — expensive, slow, and produces inconsistent interpretations. CA is the ideal first target because it has some of the most employee-protective laws in the US, creating frequent conflicts with federal baselines.

## Solution

An on-premise fine-tuned model that **extracts structured decision logic (JSON) from policy documents**. The model does NOT interpret law — it only extracts. A deterministic comparison engine then checks extracted rules against structured legislation. Lawyers review, approve/deny/edit the extractions, and edits feed back into retraining.

## Architecture

```
[Policy PDF/Text]
    → PDF parser (PyMuPDF/pdfplumber → plain text)
    → Fine-tuned Mistral 7B on BREV (inference optimized via vLLM/TGI + quantization)
    → Structured JSON output
    → Deterministic comparison engine (code, not AI)
    → Contradictions / compliance report
    → API layer (Python backend)
    → Frontend (Appwrite + custom UI — built by teammate)
    → Lawyer approves / denies / edits extractions
    → Edited outputs → retraining dataset
    → Retrain loop (via HF Jobs)
```

## Core Design Principle

The AI model does ONE thing: **extract decision logic from policy text into structured JSON**. Everything else (interpretation, contradiction detection, compliance checking) is deterministic code. This keeps the system explainable, auditable, and trustworthy.

---

## Hackathon: Mistral Worldwide Hackathon 2026 (Feb 28 – Mar 1)

### Target Prizes

| Prize                           | Sponsor        | Requirement                                                         | Fit                                           |
| ------------------------------- | -------------- | ------------------------------------------------------------------- | --------------------------------------------- |
| <$100 compute + RTX 5090        | Nvidia BREV    | Develop locally under $100 compute on BREV                          | Strong — extraction task fits 7B model        |
| Fine-Tuning Track (Global)      | W&B            | Fine-tune Mistral, prove it beats zero-shot, full pipeline with W&B | Primary track                                 |
| Self-Improvement Mini Challenge | W&B            | Best self-improvement workflow using W&B MCP Server                 | Strong — agent-driven eval→improve loop       |
| Best use of HF Jobs             | Hugging Face   | Build with HF Jobs compute                                          | Run training/inference as HF Jobs             |
| Best Architectural Modification | Tilde Research | Novel model architecture change                                     | Stretch — constrained decoding for valid JSON |
| Overall 1st/2nd/3rd             | Mistral        | Best overall project                                                | Aim for top 3                                 |

---

## End-to-End Pipelines

### User Pipeline (Compliance Officer / Lawyer)

```
1. UPLOAD    → User uploads company HR policy document (PDF/text)
2. PARSE     → PDF/text parsed to plain text (PyMuPDF/pdfplumber), chunked by section
3. EXTRACT   → Fine-tuned Mistral reads each chunk via prompt template, outputs structured JSON rules
4. COMPARE   → Deterministic engine checks rules against CA + Federal legislation JSON
5. REPORT    → User sees compliance report: pass / contradict / missing per rule
6. REVIEW    → Lawyer sees original policy text side-by-side with extracted logic + conflicting legislation
7. ACTION    → Lawyer approves, denies, or edits each extraction
8. OUTPUT    → Final compliance report generated, edited extractions saved as retraining signal
```

### Developer Pipeline (Build & Improve)

```
1. SCHEMA     → Define JSON structure for decision logic
2. DATA       → Generate 500+ synthetic policy→JSON pairs (CA + Federal scope)
3. BASELINE   → Zero-shot Mistral extraction, log to W&B → measure how bad it is
4. TRAIN      → Fine-tune on BREV with Unsloth, log everything to W&B Models
5. EVAL       → Compare fine-tuned vs zero-shot, prove improvement via W&B Weave
6. DEPLOY     → Model deployed on BREV with inference optimization (vLLM/TGI + quantization), Weave traces every call
7. FEEDBACK   → Lawyer edits flow back as training signal
8. IMPROVE    → W&B MCP agent identifies weak categories → generates targeted data → retrains → evaluates → repeats
```

### Self-Improvement Loop (W&B MCP Agent — runs autonomously)

```
1. INSPECT    → Agent pulls metrics from latest run via W&B MCP
2. DIAGNOSE   → Finds weakest rule_type category
3. GENERATE   → Creates targeted synthetic data for that category (via HF Jobs)
4. VALIDATE   → Runs data validation job (via HF Jobs)
5. RETRAIN    → Kicks off fine-tuning job (via HF Jobs — BREV stays serving live)
6. EVALUATE   → Runs batch eval job (via HF Jobs), results logged to W&B Weave
7. COMPARE    → Agent compares metrics against previous run via W&B MCP
8. DECIDE     → If accuracy_delta > threshold → go to step 2; else → stop
9. REPORT     → Agent generates W&B Report summarizing the full cycle
```

---

## Detailed Build Plan

### Phase 1: Schema Design (FIRST — everything depends on this)

Design the JSON schema for extracted decision logic. This is the contract between the model, the comparison engine, and the lawyer UI.

**Schema structure:**

```json
{
  "rules": [
    {
      "rule_id": "string",
      "rule_type": "entitlement | restriction | eligibility | termination | leave | compensation",
      "conditions": [
        {
          "field": "string (e.g. employee.location, employee.tenure_years)",
          "operator": "eq | neq | gt | gte | lt | lte | in | not_in",
          "value": "string | number | array"
        }
      ],
      "condition_logic": "all | any",
      "action": {
        "type": "grant | deny | require | notify",
        "subject": "string (what is being granted/denied)",
        "parameters": {}
      },
      "source_text": "string (verbatim excerpt from policy)",
      "confidence": "high | medium | low"
    }
  ],
  "metadata": {
    "policy_name": "string",
    "effective_date": "string",
    "applicable_jurisdictions": ["string"]
  }
}
```

**Legislation schema (same structure, used by comparison engine):**

```json
{
  "legislation": {
    "name": "California WARN Act",
    "jurisdiction": "CA | federal",
    "effective_date": "string",
    "source_url": "string"
  },
  "rules": [
    {
      "rule_id": "ca_warn_001",
      "rule_type": "restriction",
      "conditions": [
        { "field": "employer.employee_count", "operator": "gte", "value": 75 }
      ],
      "condition_logic": "all",
      "action": {
        "type": "require",
        "subject": "layoff_notice",
        "parameters": { "notice_days": 60 }
      },
      "source_text": "Cal. Lab. Code § 1400-1408..."
    }
  ]
}
```

**Prompt template (used for both fine-tuning and inference):**

```
<s>[INST] Extract all decision rules from the following company policy into structured JSON. Output only valid JSON matching the schema. Do not interpret or evaluate the rules — only extract them.

Policy text:
{policy_text}
[/INST]
```

**Deliverables:**

- `schema/decision_logic.json` — extraction output schema
- `schema/legislation.json` — legislation input schema
- `schema/prompt_template.txt` — prompt template

---

### Phase 2: Synthetic Dataset Generation (500+ samples)

Generate training pairs: `{policy_text} → {structured_json}`

**Approach:**

1. Use a strong API model (Claude) to generate realistic policy paragraphs and their corresponding JSON extractions
2. **Scope all policies to California + Federal jurisdiction** — cover all 5 target law pairs (WARN, final paycheck, PFL/FMLA, overtime, meal breaks)
3. Cover all `rule_type` categories evenly
4. Use **contrastive pairs** — for each policy, generate a clear version and an ambiguous version to teach the model boundary cases
5. Vary policy writing styles: formal legal, corporate HR, plain language
6. Include multi-rule paragraphs (one paragraph → multiple JSON rules)
7. Include policies that reference CA-specific rules, federal-only rules, and policies that mix both

**Dataset split:**

- 400 training samples
- 50 validation samples
- 50 test samples (held out, never seen during training)

**Format:** JSONL files compatible with Mistral fine-tuning format (chat completion format with system/user/assistant messages)

**Data quality validation (before training):**

1. Parse every generated JSON — reject samples where output is not valid JSON
2. Schema validation — every sample must match `schema/decision_logic.json`
3. Source text check — every `source_text` field must appear verbatim in the input policy
4. Manual spot-check — review 20-30 random samples for correctness
5. Distribution check — verify even coverage across rule_types and law topics

**Host dataset on Hugging Face Hub** — push as a public dataset for reproducibility and HF prize visibility

**Deliverables:**

- `data/train.jsonl` — 400 samples
- `data/val.jsonl` — 50 samples
- `data/test.jsonl` — 50 samples
- `data/generation_script.py` — reproducible generation pipeline
- `data/validate_data.py` — data quality validation script
- Dataset published on HF Hub (`redline-compliance-extraction`)

---

### Phase 3: Baseline — Zero-Shot Evaluation

Before fine-tuning, establish baseline performance of vanilla Mistral on the extraction task.

**Metrics to capture (all logged to W&B Models):**

- **Schema validity rate** — % of outputs that parse as valid JSON matching our schema
- **Field-level accuracy** — per-field exact match (conditions, operators, actions)
- **Rule detection recall** — did it find all rules in a paragraph
- **Rule detection precision** — did it hallucinate rules that aren't there
- **Source text alignment** — does the `source_text` field map to the right excerpt

**Log everything to W&B Models** from the start.

**Deliverables:**

- `eval/baseline_eval.py` — evaluation script
- W&B run with baseline metrics logged
- Baseline numbers documented

---

### Phase 4: Fine-Tuning on Nvidia BREV

Fine-tune Mistral 7B (or Ministral) using Unsloth for efficiency.

**Setup:**

- Platform: Nvidia BREV (stay under $100 total compute)
- Framework: Unsloth (4-bit QLoRA)
- Model: Mistral 7B or Ministral 8B
- Training: SFT on policy→JSON pairs

**W&B Models — Training Parameters (logged every run):**

- `wandb.init()` on every training run
- **Training metrics (per step):** loss, learning_rate, epoch, gradient_norm
- **Eval metrics (per eval step):**
  - `eval/schema_validity_rate` — % outputs that parse as valid JSON matching schema
  - `eval/field_accuracy_conditions` — exact match on conditions array
  - `eval/field_accuracy_operators` — exact match on operators
  - `eval/field_accuracy_actions` — exact match on action objects
  - `eval/field_accuracy_source_text` — overlap score for source text extraction
  - `eval/rule_detection_recall` — found all rules in paragraph
  - `eval/rule_detection_precision` — no hallucinated rules
  - `eval/per_type/entitlement` — accuracy on entitlement rules
  - `eval/per_type/restriction` — accuracy on restriction rules
  - `eval/per_type/leave` — accuracy on leave rules
  - `eval/per_type/termination` — accuracy on termination rules
  - `eval/per_type/compensation` — accuracy on compensation rules
  - `eval/per_type/eligibility` — accuracy on eligibility rules
  - `eval/json_structural_correctness` — valid JSON but wrong schema vs invalid JSON
  - `eval/token_efficiency` — output token count vs ground truth token count
  - `eval/confidence_calibration` — when model says "high", is it actually correct more often
- **Artifacts:** LoRA adapters logged as W&B Artifacts, pushed to HF Hub
- **Tables:** W&B Tables with sample predictions vs ground truth per eval step

**Hyperparameter config (logged to W&B):**

- LoRA rank, alpha, dropout
- Learning rate, warmup steps, scheduler type
- Batch size, gradient accumulation steps, epochs
- Quantization config (bits, quant_type, compute_dtype)
- Max sequence length, packing strategy

**Deliverables:**

- `training/finetune.py` — training script
- `training/config.yaml` — hyperparameter config
- LoRA adapter on HF Hub
- W&B dashboard with all training runs

---

### Phase 5: Inference Deployment on BREV

Deploy the fine-tuned model on BREV with inference optimization — this is key for the Nvidia prize.

**Inference optimization techniques:**

- **vLLM or TGI (Text Generation Inference)** — optimized serving with continuous batching, PagedAttention
- **GPTQ / AWQ quantization** — 4-bit quantized model for faster inference and lower memory
- **KV cache optimization** — since our outputs are structured JSON, we can tune cache allocation
- **Guided/constrained decoding** — force valid JSON output using grammar-based decoding (vLLM supports this via `outlines`). This eliminates malformed JSON entirely — strong angle for Tilde Research architectural modification prize

**Metrics to track (logged to W&B):**

- `inference/latency_p50_ms` — median inference time
- `inference/latency_p95_ms` — tail latency
- `inference/throughput_tokens_per_sec` — generation speed
- `inference/memory_usage_gb` — GPU memory footprint
- `inference/cost_per_extraction` — compute cost per policy chunk

**BREV deployment:**

- Model served as an API endpoint on BREV instance
- Frontend (teammate's Appwrite app) calls this endpoint
- Stay within the <$100 total compute budget (training + inference combined)

**Deliverables:**

- `serving/serve.py` — vLLM/TGI serving script with optimizations
- `serving/config.yaml` — quantization and serving config
- Benchmark results logged to W&B

---

### Phase 6: Post-Fine-Tune Evaluation

Run the same eval suite from Phase 3 on the fine-tuned model.

**Key comparison (this wins the W&B track):**

- Zero-shot vs fine-tuned on every metric
- Show that fine-tuning meaningfully improves extraction quality
- Especially: schema validity rate should jump significantly

**W&B Weave — Tracing & Evaluation Parameters:**

- Trace every extraction call through Weave
- **Per-trace attributes:**
  - `input_policy_text` — raw input
  - `raw_model_output` — raw string before parsing
  - `parsed_json` — parsed extraction (or parse error)
  - `latency_ms` — inference time
  - `token_count_input` — prompt tokens used
  - `token_count_output` — completion tokens used
  - `rule_count_expected` — ground truth number of rules
  - `rule_count_extracted` — model's number of rules
- **Custom Weave Scorers:**
  - `SchemaValidityScorer` — binary, does output match JSON schema
  - `FieldAccuracyScorer` — per-field exact match breakdown
  - `RuleDetectionScorer` — precision + recall on rule count
  - `SourceTextOverlapScorer` — does `source_text` actually appear verbatim in input
  - `ConfidenceCalibrationScorer` — correlation between confidence tag and actual correctness
  - `FailureModeScorer` — categorizes errors: missing_field, wrong_operator, hallucinated_rule, malformed_json, wrong_value, extra_field
- **Weave Evaluation Dashboard:** side-by-side zero-shot vs fine-tuned across all scorers

**Deliverables:**

- Side-by-side comparison in W&B
- Weave traces for all eval samples
- Clear proof that fine-tuning > zero-shot

---

### Phase 7: Deterministic Comparison Engine

Code (not AI) that checks extracted JSON rules against structured legislation.

**Approach:**

- Represent all 5 CA + Federal law pairs as structured JSON (manually authored, same schema as extraction output)
- Comparison logic: for each extracted rule, find matching legislation rules by topic/rule_type and check for conflicts
- Conflict types: contradicts, exceeds, falls_short, missing_requirement, no_federal_equivalent

**Jurisdiction scope: California + Federal only**

**Target legislation pairs for demo:**

| Topic             | CA Law                               | Federal Law                                | Conflict Type                       |
| ----------------- | ------------------------------------ | ------------------------------------------ | ----------------------------------- |
| Layoff notice     | CA WARN Act (60 days, 75+ employees) | Federal WARN Act (60 days, 100+ employees) | Different employee thresholds       |
| Final paycheck    | Due immediately on termination       | Next regular payday                        | Timing conflict                     |
| Paid family leave | CA PFL (8 weeks, 60-70% pay)         | FMLA (12 weeks, unpaid)                    | Paid vs unpaid, different durations |
| Overtime          | Daily OT after 8hrs                  | Weekly OT after 40hrs only                 | Daily vs weekly calculation         |
| Meal breaks       | Required 30min after 5hrs            | No federal requirement                     | Exists vs doesn't exist             |

**Deliverables:**

- `engine/comparator.py` — comparison logic
- `engine/legislation/` — structured legislation JSON files
- `engine/report.py` — generates compliance report from comparison

---

### Phase 8: API Layer + Frontend

**Frontend (teammate's responsibility):** Appwrite backend + custom frontend UI

**API layer (our responsibility):** Python API that the frontend calls

**API endpoints:**

- `POST /upload` — accepts policy PDF/text, returns job ID
- `GET /extract/{job_id}` — returns extracted JSON rules
- `GET /compare/{job_id}` — returns compliance report (extracted rules vs legislation)
- `POST /review/{job_id}` — accepts lawyer edits (approve/deny/edit per rule)
- `GET /report/{job_id}` — returns final compliance report

**What the frontend shows (teammate builds this):**

- Upload policy document
- View extracted decision logic as editable JSON
- Side-by-side: policy text | extracted JSON | comparison results
- Approve / Deny / Edit buttons per rule

**What we build:**

- API server exposing the extraction + comparison pipeline
- Lawyer edits received via API saved to `data/lawyer_edits/`

**Deliverables:**

- `api/server.py` — API layer (FastAPI)
- `api/models.py` — request/response schemas
- API docs for teammate to integrate with frontend

---

### Phase 9: W&B Self-Improvement Loop (Mini Challenge)

This is specifically about using the **W&B MCP Server** so that a coding agent (Claude Code) drives the improvement cycle automatically.

**The workflow:**

1. Claude Code uses W&B MCP to pull metrics from the latest training run
2. Inspects per-category accuracy (which rule types is the model worst at?)
3. Automatically generates targeted synthetic data for weak categories
4. Pushes updated dataset to HF Hub → triggers HF Jobs webhook pipeline (validate → retrain → eval)
5. Uses W&B MCP to pull eval results from the new run
6. Compares metrics against previous run
7. Repeats until metrics plateau or time runs out
8. Generates W&B Report summarizing the full improvement cycle

**W&B MCP tools used:**

- Analyze experiment runs ("show me accuracy by rule_type for run X")
- Compare runs ("compare run X vs run Y")
- Create W&B Report summarizing the improvement cycle

**W&B MCP — Self-Improvement Parameters (tracked across cycles):**

_Improvement signal metrics:_

- `cycle/lawyer_edit_distance` — avg JSON diff size between model output and lawyer correction (should decrease)
- `cycle/rejection_rate` — % of extractions fully rejected by lawyer (should decrease)
- `cycle/approval_rate` — % approved without edits (should increase)
- `cycle/edit_type_breakdown` — counts per error type: missing_field, wrong_operator, wrong_value, hallucinated_field, extra_field, wrong_rule_type

_Per-category tracking:_

- `cycle/accuracy/entitlement` — per rule type, tracked across cycles
- `cycle/accuracy/restriction`
- `cycle/accuracy/leave`
- `cycle/accuracy/termination`
- `cycle/accuracy/compensation`
- `cycle/accuracy/eligibility`
- `cycle/weakest_category` — auto-identified by MCP agent each cycle

_Dataset evolution:_

- `cycle/dataset_version` — W&B Artifact version (v1, v2, v3...)
- `cycle/dataset_size_total` — total samples
- `cycle/dataset_size_synthetic` — synthetic count
- `cycle/dataset_size_lawyer_corrected` — lawyer-corrected count
- `cycle/targeted_samples_added` — how many new samples generated for weak category

_Improvement proof:_

- `cycle/accuracy_delta` — overall accuracy change from previous cycle
- `cycle/targeted_generation_roi` — accuracy change in the specific category that was targeted
- `cycle/convergence_signal` — delta < threshold = stop retraining

**Deliverables:**

- Working MCP-driven improvement loop
- W&B Report showing improvement over cycles
- Generated skills/prompts submitted for judging
- Fill out the Self-Improvement Challenge Feedback Form

---

### Phase 10: Hugging Face Integration (HF Hub + HF Jobs)

HF Hub is the hosting layer. HF Jobs is the ML CI/CD — it runs compute jobs without touching the live BREV serving instance.

**HF Hub — Model & Dataset Hosting:**

- Push fine-tuned LoRA adapter to HF Hub with a proper model card
  - Model card: task description, schema, training details, eval results, usage instructions
- Push synthetic dataset to HF Hub as a public dataset (`redline-compliance-extraction`)
  - Dataset card: schema, generation method, distribution stats, intended use
- Version both with each self-improvement cycle (model v1, v2... dataset v1, v2...)

**HF Jobs — ML CI/CD Pipeline (this is the core HF Jobs story):**

HF Jobs acts as the automated ML operations layer. BREV stays free to serve live inference while HF Jobs handles all background compute:

1. **Synthetic data generation job** — GPU-accelerated batch generation of training pairs. Spin up a job, generate samples, push to HF Hub dataset. (`jobs/generate_data.yaml`)
2. **Data validation job** — after generation, run schema validation + source text checks + distribution analysis on the full dataset as a dedicated job. (`jobs/validate_data.yaml`)
3. **Retraining job** — when the self-improvement loop identifies weak categories and generates new data, HF Jobs runs the fine-tuning. BREV keeps serving the current model while the next version trains on HF Jobs. (`jobs/retrain.yaml`)
4. **Batch evaluation job** — run the full eval suite (all Weave scorers) against the test set after each retrain. Results logged to W&B. (`jobs/eval.yaml`)
5. **Webhook-triggered pipeline** — dataset updated on HF Hub → webhook auto-triggers: validate → retrain → eval → push new adapter to Hub. This is a fully automated ML pipeline.

**The BREV + HF Jobs split:**

```
BREV (production box)              HF Jobs (ML CI/CD)
├── Initial fine-tuning            ├── Synthetic data generation
├── Live inference serving         ├── Data validation
├── Experimentation                ├── Retraining (improvement loop)
└── Demo                           ├── Batch evaluation
                                   └── Webhook-triggered pipelines
```

**Why this split matters:**

- BREV never goes down for retraining — live API stays up
- HF Jobs is pay-per-second — only pay when running a job
- Webhook automation means the improvement loop runs itself
- Clean separation: BREV = production, HF Jobs = operations

**HF Jobs tracking (all logged to W&B):**

- `hf_job/job_id` — HF Job identifier
- `hf_job/job_type` — generate | validate | retrain | eval
- `hf_job/duration_seconds` — how long the job ran
- `hf_job/cost_usd` — compute cost
- `hf_job/gpu_type` — what hardware was used
- `hf_job/linked_wandb_run` — corresponding W&B run ID

**Deliverables:**

- Model + model card on HF Hub
- Dataset + dataset card on HF Hub
- `jobs/generate_data.yaml` — synthetic data generation job config
- `jobs/validate_data.yaml` — data validation job config
- `jobs/retrain.yaml` — retraining job config
- `jobs/eval.yaml` — batch evaluation job config
- `jobs/webhook_config.yaml` — webhook pipeline config
- Job runner script: `jobs/run_job.py` — CLI to trigger jobs programmatically

---

### Phase 11: W&B Report & Demo Prep

**W&B Report must include:**

- Problem statement and approach
- Schema design decisions
- Zero-shot vs fine-tuned comparison (with plots)
- Training curves and optimization journey
- Self-improvement loop results
- Key findings

**Demo flow:**

1. Show the problem (policy doc + legislation)
2. Run extraction (zero-shot — mediocre results)
3. Run extraction (fine-tuned — clean JSON)
4. Show comparison engine catching a contradiction
5. Show lawyer editing an extraction
6. Show the self-improvement loop running
7. Show metrics improving in W&B

---

## Priority Order (if time is tight)

1. Schema design (Phase 1) — blocks everything
2. Synthetic dataset (Phase 2) — blocks training
3. Baseline eval with W&B (Phase 3) — establishes the "before"
4. Fine-tuning on BREV (Phase 4) — the core deliverable
5. Inference optimization on BREV (Phase 5) — deploy the model, wins Nvidia prize
6. Post-fine-tune eval (Phase 6) — proves fine-tuning works, wins W&B track
7. Comparison engine (Phase 7) — makes the demo compelling
8. API layer (Phase 8) — connects model to teammate's frontend
9. Self-improvement loop with W&B MCP (Phase 9) — wins mini challenge
10. HF Hub + HF Jobs integration (Phase 10) — extra prize
11. W&B Report (Phase 11) — required for judging

---

## Tech Stack

- **Model:** Mistral 7B / Ministral 8B
- **Fine-tuning:** Unsloth (QLoRA), potentially W&B Training (ART/OpenPipe)
- **Inference serving:** vLLM or TGI with constrained JSON decoding (outlines)
- **Compute (training + inference):** Nvidia BREV (<$100 total)
- **Compute (eval/retrain loop):** HF Jobs (pay-per-second GPU)
- **Model hosting:** Hugging Face Hub (LoRA adapter + model card)
- **Dataset hosting:** Hugging Face Hub (public dataset + dataset card)
- **Experiment tracking:** W&B Models
- **Tracing & eval:** W&B Weave
- **Agent improvement:** W&B MCP Server
- **API:** FastAPI (Python backend exposing extraction + comparison endpoints)
- **Frontend:** Appwrite + custom UI (teammate)
- **PDF parsing:** PyMuPDF or pdfplumber
- **Language:** Python
- **Dataset format:** JSONL (Mistral chat completion format)

---

## File Structure

```
redline/
├── CLAUDE.md                    # This file
├── schema/
│   ├── decision_logic.json      # Extraction output schema
│   ├── legislation.json         # Legislation input schema
│   └── prompt_template.txt      # Prompt template for model
├── data/
│   ├── train.jsonl              # Training data
│   ├── val.jsonl                # Validation data
│   ├── test.jsonl               # Test data
│   ├── lawyer_edits/            # Human corrections
│   ├── generation_script.py     # Synthetic data pipeline
│   └── validate_data.py         # Data quality validation
├── eval/
│   ├── baseline_eval.py         # Zero-shot evaluation
│   ├── finetuned_eval.py        # Post-training evaluation
│   └── scorers.py               # W&B Weave custom scorers
├── training/
│   ├── finetune.py              # Training script (Unsloth + W&B)
│   └── config.yaml              # Hyperparameters
├── engine/
│   ├── comparator.py            # Deterministic comparison logic
│   ├── report.py                # Compliance report generator
│   ├── pdf_parser.py            # PDF → plain text extraction
│   └── legislation/             # Structured legislation JSON (CA + Federal)
│       ├── ca_warn.json
│       ├── federal_warn.json
│       ├── ca_final_paycheck.json
│       ├── federal_final_paycheck.json
│       ├── ca_pfl.json
│       ├── federal_fmla.json
│       ├── ca_overtime.json
│       ├── federal_overtime.json
│       ├── ca_meal_breaks.json
│       └── federal_meal_breaks.json
├── api/
│   ├── server.py                # FastAPI backend
│   └── models.py                # Request/response schemas
├── serving/
│   ├── serve.py                 # vLLM/TGI inference server
│   └── config.yaml              # Quantization + serving config
├── jobs/
│   ├── generate_data.yaml       # HF Jobs: synthetic data generation
│   ├── validate_data.yaml       # HF Jobs: data quality validation
│   ├── retrain.yaml             # HF Jobs: fine-tuning
│   ├── eval.yaml                # HF Jobs: batch evaluation
│   ├── webhook_config.yaml      # HF Jobs: webhook pipeline config
│   └── run_job.py               # CLI to trigger HF Jobs programmatically
├── mcp/                         # W&B MCP self-improvement scripts
├── requirements.txt             # Project dependencies
└── README.md                    # For HF Hub / GitHub
```
