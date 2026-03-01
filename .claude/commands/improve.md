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

Identify the weakest rule_type category (lowest `eval/per_type/*` value).

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

If traces exist, show a sample. If not, note that the next eval run will create them.

## Step 5 — TRIGGER RETRAIN
Ask the user: "Trigger the retrain pipeline now? (yes/no)"

If yes, use the Bash tool to fire the trigger:

```bash
curl -s -X POST "http://35.245.2.116:8000/retrain/trigger" \
  -H "Content-Type: application/json" | python3 -m json.tool
```

Then check status:

```bash
curl -s "http://35.245.2.116:8000/retrain/status" | python3 -m json.tool
```

Report whether `triggered: true` and the current `corrections_since_last_retrain` count. If 409 (already in progress), report that and skip.

## Step 6 — REPORT
Use `create_wandb_report_tool` to create a W&B Report summarizing:
- What was found (metrics from Step 1)
- What the weakest category is and why (Step 2)
- The delta from the previous cycle (Step 3)
- Weave evaluation status (Step 4)
- Whether retrain was triggered and its status (Step 5)

Entity: `khushiyant-personal` | Project: `redline-compliance`

Title format: `Redline Self-Improvement Report — Cycle N (MCP Agent Run)`

After creating the report, output the URL and a concise summary of findings.
