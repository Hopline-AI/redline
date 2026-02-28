"""Self-improvement loop parameters.

Every threshold is derived from statistical properties of our evaluation
setup (50 test samples, 6 rule_type categories, 8 failure modes).

With n=50 test samples and binary accuracy per sample, the standard error
of a proportion p is SE = sqrt(p*(1-p)/n). At p=0.5 (worst case),
SE = sqrt(0.25/50) = 0.0707. At p=0.8, SE = 0.0566.

Thresholds are calibrated relative to these standard errors so that
observed improvements exceed statistical noise.
"""

# ---------------------------------------------------------------------------
# W&B project coordinates
# ---------------------------------------------------------------------------
WANDB_PROJECT = "redline-compliance"
WANDB_ENTITY = "khushiyant-personal"

# ---------------------------------------------------------------------------
# Composite score weights (sum to 1.0)
#
# Rationale:
#   - schema_validity is a gating metric: if JSON doesn't parse, all
#     downstream metrics are 0. Weight 0.15 because once fine-tuned
#     it should be near 1.0 quickly.
#   - field_accuracy and rule_detection_f1 are the core extraction
#     quality signals. Each gets 0.25.
#   - source_text_overlap measures faithfulness / grounding. 0.15.
#   - min_per_type_accuracy uses a Rawlsian fairness criterion: the
#     composite is only as strong as the weakest category. 0.20.
# ---------------------------------------------------------------------------
COMPOSITE_WEIGHTS = {
    "schema_validity_rate": 0.15,
    "field_accuracy": 0.25,
    "rule_detection_f1": 0.25,
    "source_text_overlap": 0.15,
    "min_per_type_accuracy": 0.20,
}

# ---------------------------------------------------------------------------
# Rule types and their W&B metric keys
# ---------------------------------------------------------------------------
RULE_TYPES = [
    "entitlement", "restriction", "eligibility",
    "termination", "leave", "compensation",
]

RULE_TYPE_METRIC_PREFIX = "eval/per_type/"

# Failure modes tracked by FailureModeScorer
FAILURE_MODES = [
    "missing_field", "wrong_operator", "hallucinated_rule", "malformed_json",
    "wrong_value", "extra_field", "wrong_rule_type", "missing_rule",
]

# ---------------------------------------------------------------------------
# Targeting strategy
#
# We use an Expected Improvement (EI) heuristic to select which category
# to target next. EI(cat) = (target_accuracy - current_accuracy) * responsiveness.
#
# responsiveness is estimated from previous cycles: how much accuracy
# improved per N samples added. If no prior data, use DEFAULT_RESPONSIVENESS.
# ---------------------------------------------------------------------------
TARGET_ACCURACY = 0.92  # aspirational ceiling per category
DEFAULT_RESPONSIVENESS = 0.50  # prior: adding N samples yields ~50% of the gap
CATEGORY_FLOOR = 0.70  # below this, a category is definitely a candidate

# ---------------------------------------------------------------------------
# Sample generation per cycle
#
# Starts at BASE_SAMPLES_PER_CYCLE and increases linearly because later
# cycles target harder problems that need more diverse examples.
# Capped at MAX_SAMPLES_PER_CYCLE to prevent dataset imbalance.
#
# cycle 1: 30, cycle 2: 45, cycle 3: 60, cycle 4: 75, cycle 5: 80
# ---------------------------------------------------------------------------
BASE_SAMPLES_PER_CYCLE = 30
SAMPLE_INCREMENT_PER_CYCLE = 15
MAX_SAMPLES_PER_CYCLE = 80

# ---------------------------------------------------------------------------
# Failure-mode-aware generation strategies
#
# When generating targeted data, we weight the generation prompt based on
# which failure modes dominate in the weak category.
# ---------------------------------------------------------------------------
FAILURE_MODE_STRATEGIES = {
    "wrong_operator": {
        "instruction": "Include conditions with subtle operator distinctions: "
                       "'at least' vs 'more than' (gte vs gt), 'within' vs 'up to' "
                       "(lte vs lt), 'one of' vs 'equal to' (in vs eq). Make the "
                       "operator choice non-obvious from surface text.",
        "contrastive_bias": "ambiguous",
    },
    "missing_rule": {
        "instruction": "Write multi-rule paragraphs where 2-4 rules are embedded "
                       "in flowing prose without clear structural separation. Rules "
                       "should be interleaved with contextual text.",
        "contrastive_bias": "ambiguous",
    },
    "hallucinated_rule": {
        "instruction": "Write paragraphs that reference related topics in passing "
                       "but only contain 1-2 actual extractable rules. Include "
                       "informational context that is NOT a rule to test whether "
                       "the model correctly ignores non-rule content.",
        "contrastive_bias": "clear",
    },
    "wrong_value": {
        "instruction": "Include precise numeric thresholds, dates, percentages, "
                       "and employee counts. Use values that are close to but "
                       "different from standard legislative values to test "
                       "extraction precision (e.g., 65 days instead of 60).",
        "contrastive_bias": "clear",
    },
    "missing_field": {
        "instruction": "Write policies where conditions are stated implicitly "
                       "rather than explicitly. For example, 'California employees' "
                       "implies location=CA without stating it as a condition. "
                       "The model must infer all implicit conditions.",
        "contrastive_bias": "ambiguous",
    },
    "wrong_rule_type": {
        "instruction": "Include rules where the type distinction is subtle: "
                       "an 'entitlement' that looks like 'eligibility', a "
                       "'restriction' that looks like 'compensation'. Use edge "
                       "cases where the rule_type requires careful reading.",
        "contrastive_bias": "ambiguous",
    },
    "extra_field": {
        "instruction": "Write policies that mention many contextual details "
                       "(department names, job titles, dates) but only some are "
                       "actual conditions. Test whether the model correctly "
                       "identifies which details are conditions vs. context.",
        "contrastive_bias": "clear",
    },
    "malformed_json": {
        "instruction": "Write complex multi-rule policies with nested conditions "
                       "and detailed parameters to stress-test JSON generation "
                       "fidelity. Include edge cases like empty parameter objects "
                       "and single-element arrays.",
        "contrastive_bias": "clear",
    },
}

# ---------------------------------------------------------------------------
# Convergence criteria
#
# With 50 test samples, a 0.015 change in overall composite corresponds to
# roughly 0.75 samples changing outcome, which is below the noise floor.
# We require 2 consecutive cycles below threshold to confirm convergence
# (not a single fluke).
#
# Per-category regression tolerance of 0.08 is ~1.1 SE at p=0.8 (n=50),
# meaning a real regression vs. noise at roughly 87% confidence.
# ---------------------------------------------------------------------------
CONVERGENCE_DELTA_THRESHOLD = 0.015  # stop if composite improves < this
CONVERGENCE_PATIENCE = 2  # consecutive sub-threshold cycles before stopping
TARGETED_IMPROVEMENT_FLOOR = 0.02  # if the targeted category didn't improve by this, targeting failed
REGRESSION_TOLERANCE = 0.08  # flag if any non-targeted category drops by this much
REGRESSION_ABORT_THRESHOLD = 0.12  # abort cycle if any category drops by this much
MAX_CYCLES = 5  # hard limit for hackathon time budget

# ---------------------------------------------------------------------------
# Data split ratios (for augmented data integration)
# New targeted samples are added to training set only. Validation and test
# sets remain fixed to ensure consistent evaluation across cycles.
# ---------------------------------------------------------------------------
TRAIN_JSONL = "data/train.jsonl"
VAL_JSONL = "data/val.jsonl"
TEST_JSONL = "data/test.jsonl"

# ---------------------------------------------------------------------------
# GraphQL query templates for W&B MCP
# ---------------------------------------------------------------------------
GQL_LATEST_RUN = """
query LatestRun($project: String!, $entity: String!) {
  project(name: $project, entityName: $entity) {
    runs(first: 1, order: "-createdAt", filters: "{\\"state\\": \\"finished\\"}") {
      edges {
        node {
          id
          name
          displayName
          state
          config
          summaryMetrics
          createdAt
          heartbeatAt
          tags
        }
      }
    }
  }
}
"""

GQL_RUN_BY_NAME = """
query RunByName($project: String!, $entity: String!, $runName: String!) {
  project(name: $project, entityName: $entity) {
    runs(first: 1, filters: $runName) {
      edges {
        node {
          id
          name
          displayName
          state
          config
          summaryMetrics
          createdAt
          tags
        }
      }
    }
  }
}
"""

GQL_ALL_FINISHED_RUNS = """
query AllFinishedRuns($project: String!, $entity: String!) {
  project(name: $project, entityName: $entity) {
    runs(first: 50, order: "-createdAt", filters: "{\\"state\\": \\"finished\\"}") {
      edges {
        node {
          id
          name
          displayName
          summaryMetrics
          config
          createdAt
          tags
        }
      }
    }
  }
}
"""

# ---------------------------------------------------------------------------
# W&B Report template sections
# ---------------------------------------------------------------------------
REPORT_TITLE_TEMPLATE = "Redline Self-Improvement Report — {n_cycles} Cycles"

REPORT_SECTION_OVERVIEW = """## Overview

**Project:** {project}
**Total cycles:** {n_cycles}
**Composite score:** {initial_composite:.4f} → {final_composite:.4f} (+{composite_delta:.4f})
**Best model:** {best_run_name}
"""

REPORT_SECTION_CYCLE = """### Cycle {cycle_num}

**Target category:** `{target_category}` (accuracy: {target_accuracy_before:.4f})
**Dominant failure mode:** `{dominant_failure}`
**Samples generated:** {samples_generated}
**Dataset version:** v{dataset_version}

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Composite | {composite_before:.4f} | {composite_after:.4f} | {composite_delta:+.4f} |
| Schema validity | {schema_before:.4f} | {schema_after:.4f} | {schema_delta:+.4f} |
| Field accuracy | {field_before:.4f} | {field_after:.4f} | {field_delta:+.4f} |
| Rule detection F1 | {f1_before:.4f} | {f1_after:.4f} | {f1_delta:+.4f} |
| Target category ({target_category}) | {target_accuracy_before:.4f} | {target_accuracy_after:.4f} | {target_delta:+.4f} |

**Regressions:** {regressions}
"""
