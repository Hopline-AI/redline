"""Generate targeted synthetic data for weak categories.

Reuses the generation infrastructure from data/generation_script.py
but biases the coverage matrix toward the identified weak category
and dominant failure mode.
"""

from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

from google import genai
import jsonschema
from tenacity import retry, stop_after_attempt, wait_exponential

from self_improve.config import (
    BASE_SAMPLES_PER_CYCLE,
    FAILURE_MODE_STRATEGIES,
    MAX_SAMPLES_PER_CYCLE,
    RULE_TYPES,
    SAMPLE_INCREMENT_PER_CYCLE,
    TRAIN_JSONL,
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.field_vocabulary import CANONICAL_FIELDS, format_field_list
from data.generation_script import (
    COMPLEXITIES,
    CONFIDENCE_WEIGHTS,
    CONDITION_LOGIC_WEIGHTS,
    JURISDICTION_MIXES,
    OPERATOR_HINTS,
    TOPICS,
    WRITING_STYLES,
    build_prompt,
    parse_response,
    to_mistral_format,
    validate_sample,
)

SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "decision_logic.json"


def _load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def samples_for_cycle(cycle_num: int) -> int:
    n = BASE_SAMPLES_PER_CYCLE + SAMPLE_INCREMENT_PER_CYCLE * (cycle_num - 1)
    return min(n, MAX_SAMPLES_PER_CYCLE)


RULE_TYPE_TOPIC_AFFINITY = {
    "entitlement": ["final_paycheck", "meal_breaks", "pfl_fmla"],
    "restriction": ["warn", "overtime", "meal_breaks"],
    "eligibility": ["pfl_fmla", "warn", "overtime"],
    "termination": ["warn", "final_paycheck"],
    "leave": ["pfl_fmla"],
    "compensation": ["overtime", "meal_breaks", "final_paycheck"],
}


def build_targeted_specs(
    target_category: str,
    dominant_failure: str,
    n_samples: int,
    seed: int = 42,
) -> list[dict]:
    """Build a coverage matrix biased toward the weak category and failure mode.

    Distribution: 60% target category, 25% adjacent rule_types, 15% other
    (prevents catastrophic forgetting while focusing on the weak area).
    """
    rng = random.Random(seed)

    n_target = int(n_samples * 0.60)
    n_adjacent = int(n_samples * 0.25)
    n_other = n_samples - n_target - n_adjacent

    fm_strategy = FAILURE_MODE_STRATEGIES.get(dominant_failure, {})
    fm_instruction = fm_strategy.get("instruction", "")
    contrastive_bias = fm_strategy.get("contrastive_bias", "clear")

    # Flip weights based on failure mode so contrastive type aligns with what's hard.
    contrastive_weights = [0.3, 0.7] if contrastive_bias == "ambiguous" else [0.7, 0.3]

    preferred_topics = RULE_TYPE_TOPIC_AFFINITY.get(target_category, [t["id"] for t in TOPICS])
    topic_by_id = {t["id"]: t for t in TOPICS}

    adjacent_types = [rt for rt in RULE_TYPES if rt != target_category]

    specs = []
    spec_id = 0

    def make_spec(rule_type: str, is_targeted: bool) -> dict:
        nonlocal spec_id

        if is_targeted and preferred_topics:
            topic_id = rng.choice(preferred_topics)
            topic = topic_by_id.get(topic_id, rng.choice(TOPICS))
        else:
            topic = rng.choice(TOPICS)

        style = rng.choice(WRITING_STYLES)

        # Mixed-jurisdiction policies are harder; bias targeted samples toward them.
        juris_weights = [0.25, 0.25, 0.50] if is_targeted else [0.33, 0.33, 0.34]
        juris = rng.choices(JURISDICTION_MIXES, weights=juris_weights, k=1)[0]

        # Multi-rule paragraphs are the natural stress-test for missing/hallucinated rules.
        if dominant_failure in ("missing_rule", "hallucinated_rule"):
            complexity = COMPLEXITIES[1]  # multi
        else:
            complexity = rng.choice(COMPLEXITIES)

        contrastive = rng.choices(
            [{"id": "clear", "instruction": "Make the policy language clear and unambiguous. The rules should be easy to extract."},
             {"id": "ambiguous", "instruction": "Make the policy language somewhat ambiguous or convoluted. Include conditional clauses, exceptions, and cross-references that make extraction harder. The model should still extract the most reasonable interpretation."}],
            weights=contrastive_weights,
            k=1,
        )[0]

        # Append failure-mode guidance so targeted samples stress the exact weakness.
        if is_targeted and fm_instruction:
            contrastive = {
                "id": contrastive["id"],
                "instruction": f"{contrastive['instruction']} Additionally: {fm_instruction}",
            }

        confidence_hint = rng.choices(
            list(CONFIDENCE_WEIGHTS.keys()),
            weights=list(CONFIDENCE_WEIGHTS.values()),
            k=1,
        )[0]
        logic_hint = rng.choices(
            list(CONDITION_LOGIC_WEIGHTS.keys()),
            weights=list(CONDITION_LOGIC_WEIGHTS.values()),
            k=1,
        )[0]

        pos_in_batch = spec_id % 30
        operator_hint = OPERATOR_HINTS[pos_in_batch] if pos_in_batch < len(OPERATOR_HINTS) else None

        spec = {
            "id": f"targeted_{spec_id:04d}",
            "topic": topic,
            "rule_type": rule_type,
            "style": style,
            "jurisdiction": juris,
            "complexity": complexity,
            "contrastive": contrastive,
            "confidence_hint": confidence_hint,
            "logic_hint": logic_hint,
            "operator_hint": operator_hint,
            "targeted": True,
            "target_category": target_category,
            "dominant_failure": dominant_failure,
        }
        spec_id += 1
        return spec

    for _ in range(n_target):
        specs.append(make_spec(target_category, is_targeted=True))

    for _ in range(n_adjacent):
        rt = rng.choice(adjacent_types)
        specs.append(make_spec(rt, is_targeted=False))

    for _ in range(n_other):
        rt = rng.choice(RULE_TYPES)
        specs.append(make_spec(rt, is_targeted=False))

    rng.shuffle(specs)
    return specs


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def _generate_single(client: genai.Client, model: str, prompt: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text


def generate_targeted_samples(
    target_category: str,
    dominant_failure: str,
    cycle_num: int,
    model: str = "gemini-2.0-flash",
    seed: int = 42,
    dry_run: bool = False,
) -> list[dict]:
    """Generate targeted synthetic samples biased toward a weak category."""
    n_samples = samples_for_cycle(cycle_num)
    print(f"\nGenerating {n_samples} targeted samples for cycle {cycle_num}")
    print(f"  Target category: {target_category}")
    print(f"  Dominant failure: {dominant_failure}")
    print(f"  Failure strategy: {FAILURE_MODE_STRATEGIES.get(dominant_failure, {}).get('instruction', 'default')[:80]}...")

    specs = build_targeted_specs(target_category, dominant_failure, n_samples, seed + cycle_num)

    rt_dist = {}
    for s in specs:
        rt = s["rule_type"]
        rt_dist[rt] = rt_dist.get(rt, 0) + 1
    print(f"  Rule type distribution: {rt_dist}")

    if dry_run:
        print(f"  DRY RUN — would generate {n_samples} samples")
        print(f"  Sample prompt (first spec):")
        print(f"    {build_prompt(specs[0])[:200]}...")
        return []

    schema = _load_schema()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    api_key = line.split("=", 1)[1]
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)

    valid_samples = []
    failed = 0

    for i, spec in enumerate(specs):
        prompt = build_prompt(spec)
        print(f"  [{i+1}/{n_samples}] {spec['id']} (type={spec['rule_type']}, topic={spec['topic']['id']})...", end=" ", flush=True)

        try:
            text = _generate_single(client, model, prompt)
            policy_text, extraction, err = parse_response(text)

            if err:
                print(f"PARSE ERROR: {err}")
                failed += 1
                continue

            errors = validate_sample(policy_text, extraction, schema)
            if errors:
                print(f"VALIDATION: {errors[0]}")
                failed += 1
                continue

            valid_samples.append(to_mistral_format(policy_text, extraction))
            n_rules = len(extraction.get("rules", []))
            print(f"OK ({n_rules} rules)")

        except Exception as e:
            print(f"ERROR: {e}")
            failed += 1

    print(f"\n  Generated: {len(valid_samples)} valid, {failed} failed")
    return valid_samples


def append_to_training_data(new_samples: list[dict], train_path: str | None = None):
    path = Path(train_path or TRAIN_JSONL)

    existing_count = 0
    if path.exists():
        with open(path) as f:
            existing_count = sum(1 for line in f if line.strip())

    with open(path, "a") as f:
        for sample in new_samples:
            f.write(json.dumps(sample) + "\n")

    new_count = existing_count + len(new_samples)
    print(f"  Appended {len(new_samples)} samples to {path} (total: {new_count})")
    return new_count
