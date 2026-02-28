## Overview

**Project:** redline-compliance
**Total cycles:** 2
**Composite score:** 0.1558 → 0.1558 (+0.0000)
**Best model:** cycle_2_simulated


---

## Composite Score Design

| Metric | Weight | Rationale |
|---|---|---|
| schema_validity_rate | 0.15 | Gating metric — invalid JSON nullifies all downstream metrics |
| field_accuracy | 0.25 | Core task quality — correct conditions, operators, actions |
| rule_detection_f1 | 0.25 | Coverage and precision of rule identification |
| source_text_overlap | 0.15 | Faithfulness — extractions must be grounded in policy text |
| min_per_type_accuracy | 0.20 | Rawlsian fairness — no category left behind |

---

## Metric Progression Across Cycles

| Cycle | Composite | Schema | Fields | F1 | Source | Min Type |
|---|---|---|---|---|---|---|
| 0 | 0.1558 | 0.0435 | 0.0299 | 0.0439 | 0.8722 | 0.0000 |
| 1 | 0.1558 | 0.0435 | 0.0299 | 0.0439 | 0.8722 | 0.0000 |
| 2 | 0.1558 | 0.0435 | 0.0299 | 0.0439 | 0.8722 | 0.0000 |

---

## Per-Category Accuracy Progression

| Category | Baseline | Cycle 1 | Cycle 2 | Delta |
|---|---|---|---|---|
| entitlement | 0.0000 | 0.0000 | 0.0000 | +0.0000 |
| restriction | 0.0000 | 0.0000 | 0.0000 | +0.0000 |
| eligibility | 0.0000 | 0.0000 | 0.0000 | +0.0000 |
| termination | 0.0000 | 0.0000 | 0.0000 | +0.0000 |
| leave | 0.0000 | 0.0000 | 0.0000 | +0.0000 |
| compensation | 0.0000 | 0.0000 | 0.0000 | +0.0000 |

---

### Cycle 1

**Target category:** `entitlement` (accuracy: 0.0000)
**Dominant failure mode:** `none`
**Samples generated:** 0
**Dataset version:** v1

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Composite | 0.1558 | 0.1558 | +0.0000 |
| Schema validity | 0.0435 | 0.0435 | +0.0000 |
| Field accuracy | 0.0299 | 0.0299 | +0.0000 |
| Rule detection F1 | 0.0439 | 0.0439 | +0.0000 |
| Target category (entitlement) | 0.0000 | 0.0000 | +0.0000 |

**Regressions:** None


---

### Cycle 2

**Target category:** `restriction` (accuracy: 0.0000)
**Dominant failure mode:** `none`
**Samples generated:** 0
**Dataset version:** v2

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Composite | 0.1558 | 0.1558 | +0.0000 |
| Schema validity | 0.0435 | 0.0435 | +0.0000 |
| Field accuracy | 0.0299 | 0.0299 | +0.0000 |
| Rule detection F1 | 0.0439 | 0.0439 | +0.0000 |
| Target category (restriction) | 0.0000 | 0.0000 | +0.0000 |

**Regressions:** None


---

## Conclusion

After **2 improvement cycles**, the composite score improved from **0.1558** to **0.1558** (+0.0000).


**Stop reason:** Converged — composite delta (+0.0000) below threshold.
