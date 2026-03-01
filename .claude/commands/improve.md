Run one W&B MCP-driven self-improvement cycle for the Redline compliance model.

Execute the following steps in order, using W&B MCP tools throughout:

## Step 1 — INSPECT
Use `query_wandb_tool` to fetch the latest finished eval run from `khushiyant-personal/redline-compliance`.

```graphql
query LatestEvalRun($entity: String!, $project: String!, $filters: JSONString) {
  project(name: $project, entityName: $entity) {
    runs(first: 5, filters: $filters, order: "-createdAt") {
      edges {
        node {
          id
          name
          displayName
          state
          createdAt
          summaryMetrics
        }
      }
      pageInfo { endCursor hasNextPage }
    }
  }
}
```
Variables: `{"entity": "khushiyant-personal", "project": "redline-compliance", "filters": "{\"state\": \"finished\"}"}`

Find the most recent run that has `eval/` metrics (look for `eval/schema_validity_rate`, `eval/field_accuracy`, `eval/per_type/*`).

## Step 2 — DIAGNOSE
Parse the `summaryMetrics` from the run. Extract:
- `eval/schema_validity_rate`
- `eval/field_accuracy`
- `eval/f1`
- `eval/per_type/entitlement`, `eval/per_type/restriction`, `eval/per_type/leave`, `eval/per_type/termination`, `eval/per_type/compensation`, `eval/per_type/eligibility`
- Any `failure_modes/*` metrics

Identify the weakest rule_type category (lowest `eval/per_type/*` value that is NOT identical to schema_validity_rate — if all are identical, flag that per-type tracking needs a new eval run).

State clearly:
- Weakest category and its score
- Dominant failure mode (highest `failure_modes/*` count, or "unknown" if not logged)
- Expected Improvement: `EI = (0.90 - current_accuracy) * 0.50`

## Step 3 — COMPARE (if a previous eval run exists)
Use `query_wandb_tool` to fetch the second-most-recent eval run. Show a delta table:

| Metric | Previous | Current | Delta |
|--------|----------|---------|-------|
| schema_validity_rate | ... | ... | ... |
| field_accuracy | ... | ... | ... |
| f1 | ... | ... | ... |
| eval/per_type/<weakest> | ... | ... | ... |

## Step 4 — CHECK WEAVE TRACES
Use `query_weave_traces_tool` and `count_weave_traces_tool` to check:
- How many Weave traces exist in `khushiyant-personal/redline-compliance`
- Whether any `Evaluation` traces exist (filter by `op_name_contains: "Evaluation"`)

If traces exist, show a sample. If not, note that the next eval run (using the updated `finetuned_eval.py`) will create them.

## Step 5 — GENERATE (instruct, don't execute)
Based on the weakest category, show the exact command to generate targeted training data:

```bash
cd /home/shadeform/redline/backend
uv run python -m self_improve.orchestrate_loop --max-cycles 1 --dry-run
```

Or for targeted data only:
```bash
uv run python -c "
from self_improve.generate_targeted_data import generate_targeted_samples
samples = generate_targeted_samples('<weakest_category>', '<dominant_failure>', cycle_num=2)
print(f'Generated {len(samples)} samples')
"
```

## Step 6 — REPORT
Use `create_wandb_report_tool` to create a W&B Report summarizing:
- What was found (metrics from Step 1)
- What the weakest category is and why (Step 2)
- The delta from the previous cycle (Step 3)
- Weave evaluation status (Step 4)
- Recommended next action (Step 5)

Entity: `khushiyant-personal` | Project: `redline-compliance`

Title format: `Redline Self-Improvement Report — Cycle N (MCP Agent Run)`

After creating the report, output the URL and a concise summary of findings.
