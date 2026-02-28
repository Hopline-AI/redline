#!/usr/bin/env python3
"""Generate synthetic training data for Redline compliance extraction.

Produces policy_text → structured_JSON pairs using Google Gemini API.

Usage:
    # Dry run with 5 samples
    uv run python data/generation_script.py --target-count 5 --seed 43

    # Full generation (510 samples)
    uv run python data/generation_script.py --target-count 510 --seed 43
"""

import argparse
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

from google import genai
import jsonschema
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.insert(0, str(Path(__file__).parent.parent))
from data.field_vocabulary import CANONICAL_FIELDS, format_field_list

TOPICS = [
    {
        "id": "warn",
        "name": "WARN Act / Layoff Notice",
        "ca_law": "California WARN Act requires employers with 75 or more employees to provide 60 days advance written notice before a mass layoff, relocation, or plant closure affecting 50 or more workers.",
        "federal_law": "Federal WARN Act requires employers with 100 or more employees to provide 60 days advance notice before a plant closing or mass layoff affecting 50 or more workers.",
        "conflict": "California has a lower employee threshold (75 vs 100) for WARN applicability.",
    },
    {
        "id": "final_paycheck",
        "name": "Final Paycheck Timing",
        "ca_law": "California Labor Code Section 201-202 requires employers to pay all wages due immediately upon involuntary termination. Employees who quit with 72 hours notice must be paid on their last day; without notice, within 72 hours.",
        "federal_law": "Federal law (FLSA) requires final pay by the next regular payday. There is no federal requirement for immediate payment upon termination.",
        "conflict": "California requires immediate payment on termination vs federal next-regular-payday standard.",
    },
    {
        "id": "pfl_fmla",
        "name": "Paid Family Leave / FMLA",
        "ca_law": "California Paid Family Leave (PFL) provides up to 8 weeks of partial wage replacement (60-70% of wages) for bonding with a new child or caring for a seriously ill family member. Applies to employees who pay into SDI.",
        "federal_law": "The Family and Medical Leave Act (FMLA) provides up to 12 weeks of unpaid, job-protected leave for eligible employees at employers with 50+ employees within 75 miles. Covers birth/adoption, serious health conditions.",
        "conflict": "CA PFL provides paid leave (8 weeks at 60-70%) while FMLA provides unpaid leave (12 weeks). Different eligibility and duration.",
    },
    {
        "id": "overtime",
        "name": "Overtime Rules",
        "ca_law": "California requires overtime pay at 1.5x regular rate for hours worked over 8 in a day or 40 in a week, and 2x for hours over 12 in a day or over 8 on the 7th consecutive workday.",
        "federal_law": "The FLSA requires overtime at 1.5x regular rate only for hours worked over 40 in a workweek. There is no daily overtime requirement under federal law.",
        "conflict": "California has daily overtime (after 8 hours) while federal law only has weekly overtime (after 40 hours).",
    },
    {
        "id": "meal_breaks",
        "name": "Meal and Rest Breaks",
        "ca_law": "California requires a 30-minute unpaid meal break for shifts over 5 hours, a second meal break for shifts over 10 hours, and a paid 10-minute rest break for every 4 hours worked. Employers must pay one hour of premium pay for each missed break.",
        "federal_law": "Federal law has no meal or rest break requirements for adult employees. If an employer provides breaks of 5-20 minutes, they must be paid; meal breaks of 30+ minutes may be unpaid if the employee is fully relieved of duties.",
        "conflict": "California mandates meal and rest breaks; federal law has no such requirement for adults.",
    },
]

RULE_TYPES = ["entitlement", "restriction", "eligibility", "termination", "leave", "compensation"]

WRITING_STYLES = [
    {
        "id": "formal_legal",
        "instruction": "Write in formal legal language with section numbers, subsections, and precise legal terminology. Use phrases like 'shall', 'pursuant to', 'notwithstanding', and reference statutory provisions.",
    },
    {
        "id": "corporate_hr",
        "instruction": "Write in professional corporate HR language suitable for an employee handbook. Use clear headings, bullet points in prose form, and a professional but accessible tone.",
    },
    {
        "id": "plain_language",
        "instruction": "Write in plain, everyday language that a non-lawyer employee can understand. Use simple sentences, avoid jargon, and explain terms when used.",
    },
]

JURISDICTION_MIXES = [
    {"id": "ca_only", "instruction": "The policy applies exclusively to California employees and should reference California-specific rules."},
    {"id": "federal_only", "instruction": "The policy applies to all US employees under federal standards only, with no state-specific provisions."},
    {"id": "mixed", "instruction": "The policy covers employees in multiple states including California, referencing both California-specific and federal requirements."},
]

COMPLEXITIES = [
    {"id": "single", "instruction": "Write a policy paragraph that contains exactly ONE decision rule.", "rule_count": "1"},
    {"id": "multi", "instruction": "Write a policy paragraph that contains 2 to 4 interrelated decision rules.", "rule_count": "2-4"},
]

CONTRASTIVE_TYPES = [
    {"id": "clear", "instruction": "Make the policy language clear and unambiguous. The rules should be easy to extract."},
    {"id": "ambiguous", "instruction": "Make the policy language somewhat ambiguous or convoluted. Include conditional clauses, exceptions, and cross-references that make extraction harder. The model should still extract the most reasonable interpretation."},
]

RULE_TYPE_WEIGHTS = {
    "entitlement": 1.0,
    "restriction": 1.0,
    "eligibility": 1.15,
    "termination": 1.0,
    "leave": 1.18,
    "compensation": 0.9,
}

CONFIDENCE_WEIGHTS = {"high": 0.70, "medium": 0.20, "low": 0.10}
CONDITION_LOGIC_WEIGHTS = {"all": 0.75, "any": 0.25}

# The first N slots of every 30-sample batch are pinned to underrepresented
# operators so they can't be crowded out by weighted random sampling.
OPERATOR_HINTS = ["not_in", "not_in", "neq", "neq", "neq", "lt", "lte"]


def build_coverage_matrix(target_count: int, seed: int) -> list[dict]:
    """Build a reproducible list of sample specs with rebalanced rule-type coverage.

    Seeded so re-running with the same arguments yields an identical matrix,
    which is important for consistent train/val/test splits across runs.
    """
    rng = random.Random(seed)

    rt_names = list(RULE_TYPE_WEIGHTS.keys())
    rt_weights = [RULE_TYPE_WEIGHTS[rt] for rt in rt_names]

    specs = []
    spec_id = 0

    while len(specs) < target_count:
        rule_type = rng.choices(rt_names, weights=rt_weights, k=1)[0]
        topic = rng.choice(TOPICS)
        style = rng.choice(WRITING_STYLES)
        juris = rng.choice(JURISDICTION_MIXES)
        complexity = rng.choice(COMPLEXITIES)
        contrastive = rng.choice(CONTRASTIVE_TYPES)

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

        specs.append({
            "id": f"sample_{spec_id:04d}",
            "topic": topic,
            "rule_type": rule_type,
            "style": style,
            "jurisdiction": juris,
            "complexity": complexity,
            "contrastive": contrastive,
            "confidence_hint": confidence_hint,
            "logic_hint": logic_hint,
            "operator_hint": operator_hint,
        })
        spec_id += 1

    rng.shuffle(specs)
    return specs


GENERATION_PROMPT = """You are generating synthetic training data for a compliance AI model. Generate BOTH a realistic company HR policy document section AND its corresponding structured JSON extraction.

TOPIC: {topic_name}
California law context: {ca_law}
Federal law context: {federal_law}
Key conflict: {conflict}

REQUIREMENTS:
- The primary rule_type for the main rule(s) should be: {rule_type}
- Writing style: {style_instruction}
- Jurisdiction scope: {jurisdiction_instruction}
- Complexity: {complexity_instruction} (target {rule_count} rule(s))
- Clarity: {contrastive_instruction}

POLICY TEXT REQUIREMENTS:
- The policy text must be at least 200 words and should resemble a real corporate document.
- Include realistic details: a fictitious company name, section/policy numbers, effective dates, revision numbers.
- Where appropriate include cross-references to other policy sections, definitions clauses, or statutory citations.
- Do NOT include compensatory time off for California private-sector employees — this is illegal under CA Labor Code Section 204.

CANONICAL FIELD VOCABULARY — use ONLY these field names in conditions:
{field_list}

If a condition does not fit any canonical field, choose the closest match. Do NOT invent new field names.

OPERATOR AND ACTION DIVERSITY:
- Use the full range of operators: eq, neq, gt, gte, lt, lte, in, not_in.{operator_hint_instruction}
- Ensure the action.type reflects the rule semantics. Use 'notify' for rules requiring notification to government agencies, unions, EDD, or employees. Use 'require' for mandatory obligations. Use 'grant' for entitlements. Use 'deny' for prohibitions.

CONFIDENCE AND LOGIC:
- Set confidence to: {confidence_hint} (use 'low' when the policy text is genuinely ambiguous, 'medium' for slightly unclear wording, 'high' for clear rules).
- Use condition_logic: {logic_hint} (use 'any' when conditions are alternatives / OR, 'all' when conditions must all be met / AND).

METADATA:
- effective_date must be a specific date (e.g. '2025-01-01'), not 'current' or 'not specified'.

JSON SCHEMA:
{{
  "rules": [
    {{
      "rule_id": "string (lowercase, underscores, e.g. warn_notice_001)",
      "rule_type": "entitlement | restriction | eligibility | termination | leave | compensation",
      "conditions": [
        {{
          "field": "one of the canonical fields listed above",
          "operator": "eq | neq | gt | gte | lt | lte | in | not_in",
          "value": "string | number | boolean | array"
        }}
      ],
      "condition_logic": "all | any",
      "action": {{
        "type": "grant | deny | require | notify",
        "subject": "string (what is being granted/denied/required/notified)",
        "parameters": {{}}
      }},
      "source_text": "VERBATIM quote from the policy text above",
      "confidence": "high | medium | low"
    }}
  ],
  "metadata": {{
    "policy_name": "string",
    "effective_date": "YYYY-MM-DD",
    "applicable_jurisdictions": ["CA", "federal"] (whichever apply)
  }}
}}

OUTPUT FORMAT — use these exact delimiters:

===POLICY_TEXT_START===
(your generated policy document section here — minimum 200 words)
===POLICY_TEXT_END===
===JSON_START===
(your JSON extraction here)
===JSON_END===

Generate the output now."""


def build_prompt(spec: dict) -> str:
    operator_hint = spec.get("operator_hint")
    if operator_hint:
        operator_hint_instruction = f"\n- At least one condition MUST use the '{operator_hint}' operator."
    else:
        operator_hint_instruction = ""

    return GENERATION_PROMPT.format(
        topic_name=spec["topic"]["name"],
        ca_law=spec["topic"]["ca_law"],
        federal_law=spec["topic"]["federal_law"],
        conflict=spec["topic"]["conflict"],
        rule_type=spec["rule_type"],
        style_instruction=spec["style"]["instruction"],
        jurisdiction_instruction=spec["jurisdiction"]["instruction"],
        complexity_instruction=spec["complexity"]["instruction"],
        rule_count=spec["complexity"]["rule_count"],
        contrastive_instruction=spec["contrastive"]["instruction"],
        field_list=format_field_list(),
        operator_hint_instruction=operator_hint_instruction,
        confidence_hint=spec.get("confidence_hint", "high"),
        logic_hint=spec.get("logic_hint", "all"),
    )


def parse_response(text: str) -> tuple[str | None, dict | None, str | None]:
    """Parse a model response into (policy_text, json_dict, error)."""
    try:
        policy_start = text.index("===POLICY_TEXT_START===") + len("===POLICY_TEXT_START===")
        policy_end = text.index("===POLICY_TEXT_END===")
        policy_text = text[policy_start:policy_end].strip()
    except ValueError:
        return None, None, "missing POLICY_TEXT delimiters"

    try:
        json_start = text.index("===JSON_START===") + len("===JSON_START===")
        json_end = text.index("===JSON_END===")
        json_str = text[json_start:json_end].strip()
    except ValueError:
        return policy_text, None, "missing JSON delimiters"

    # Strip markdown code fences (e.g. ```json ... ```) that some models add
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1] if "\n" in json_str else json_str[3:]
    if json_str.endswith("```"):
        json_str = json_str[: -3].rstrip()

    try:
        json_dict = json.loads(json_str)
    except json.JSONDecodeError as e:
        return policy_text, None, f"invalid JSON: {e}"

    return policy_text, json_dict, None


def validate_sample(policy_text: str, extraction: dict, schema: dict) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors = []

    try:
        jsonschema.validate(instance=extraction, schema=schema)
    except jsonschema.ValidationError as e:
        errors.append(f"schema: {e.message}")

    for i, rule in enumerate(extraction.get("rules", [])):
        src = rule.get("source_text", "")
        if src and src not in policy_text:
            errors.append(f"rule {i} source_text not verbatim in policy")

    return errors


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=2, max=60),
    before_sleep=lambda rs: print(f"    Retry {rs.attempt_number}/5 after {rs.outcome.exception().__class__.__name__}: {rs.outcome.exception()}", flush=True),
)
def generate_single(client: genai.Client, model: str, prompt: str) -> str:
    """Generate a single sample via Gemini API."""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text


SYSTEM_MESSAGE = (
    "You are a compliance extraction engine. Your task is to extract all decision "
    "rules from company policy documents into structured JSON. Output only valid JSON "
    "matching the provided schema. Do not interpret, evaluate, or offer opinions on "
    "the rules — only extract them exactly as stated in the policy text.\n\n"
    "Allowed condition field names (use ONLY these):\n"
    "  employee.location_state, employee.classification, employee.employment_status,\n"
    "  employee.tenure_months, employee.hours_worked_weekly, employee.hours_worked_daily,\n"
    "  employee.hours_worked_12_months, employee.pay_type, employee.age, employee.leave_type,\n"
    "  employee.sdi_contributor, employee.shift_hours, employee.consecutive_workdays,\n"
    "  employer.employee_count, employer.employee_count_within_75_miles, employer.location_state,\n"
    "  termination.type, termination.notice_given, termination.notice_hours,\n"
    "  layoff.affected_employee_count, layoff.type, layoff.timeframe_days,\n"
    "  leave.type, leave.duration_weeks, leave.reason,\n"
    "  break.type, break.duration_minutes,\n"
    "  shift.start_time, shift.duration_hours"
)

USER_TEMPLATE = (
    "Extract all decision rules from the following company policy into structured JSON. "
    "For each rule, identify the rule type, conditions, actions, and include the exact "
    "source text from the policy.\n\nPolicy text:\n{policy_text}"
)


def to_mistral_format(policy_text: str, extraction: dict) -> dict:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": USER_TEMPLATE.format(policy_text=policy_text)},
            {"role": "assistant", "content": json.dumps(extraction, indent=2)},
        ]
    }


def stratified_split(
    samples: list[dict], specs: list[dict], train_n: int, val_n: int, test_n: int, seed: int
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split samples preserving topic×rule_type distribution."""
    rng = random.Random(seed)

    # Group by topic×rule_type
    groups: dict[str, list[tuple[dict, dict]]] = {}
    for sample, spec in zip(samples, specs):
        key = f"{spec['topic']['id']}_{spec['rule_type']}"
        groups.setdefault(key, []).append((sample, spec))

    train, val, test = [], [], []
    total = train_n + val_n + test_n

    for key, items in groups.items():
        rng.shuffle(items)
        n = len(items)
        n_test = max(1, round(n * test_n / total))
        n_val = max(1, round(n * val_n / total))
        n_train = n - n_test - n_val

        test.extend([s for s, _ in items[:n_test]])
        val.extend([s for s, _ in items[n_test : n_test + n_val]])
        train.extend([s for s, _ in items[n_test + n_val :]])

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def write_jsonl(path: Path, samples: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for sample in samples:
            f.write(json.dumps(sample) + "\n")
    print(f"Wrote {len(samples)} samples to {path}")


def main():
    parser = argparse.ArgumentParser(description="Generate Redline training data")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Gemini model to use")
    parser.add_argument("--target-count", type=int, default=510, help="Number of samples to generate")
    parser.add_argument("--output-dir", default="data", help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--schema-path", default="schema/decision_logic.json", help="Path to JSON schema")
    args = parser.parse_args()

    with open(args.schema_path) as f:
        schema = json.load(f)

    specs = build_coverage_matrix(args.target_count, args.seed)
    print(f"Built coverage matrix: {len(specs)} specs")

    topic_dist = Counter(s["topic"]["id"] for s in specs)
    rt_dist = Counter(s["rule_type"] for s in specs)
    print(f"  Topics: {dict(topic_dist)}")
    print(f"  Rule types: {dict(rt_dist)}")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1]
        if not api_key:
            print("ERROR: Set GEMINI_API_KEY environment variable")
            sys.exit(1)

    client = genai.Client(api_key=api_key)

    valid_samples = []
    valid_specs = []
    failed_specs = []

    for i, spec in enumerate(specs):
        prompt = build_prompt(spec)
        print(f"[{i+1}/{len(specs)}] Generating {spec['id']} "
              f"(topic={spec['topic']['id']}, type={spec['rule_type']})...", flush=True)
        try:
            text = generate_single(client, args.model, prompt)
        except Exception as e:
            print(f"  API error: {e}")
            failed_specs.append(spec)
            continue

        policy_text, extraction, err = parse_response(text)
        if err:
            print(f"  Parse error: {err}")
            failed_specs.append(spec)
            continue

        errors = validate_sample(policy_text, extraction, schema)
        if errors:
            print(f"  Validation errors: {errors}")
            failed_specs.append(spec)
            continue

        valid_samples.append(to_mistral_format(policy_text, extraction))
        valid_specs.append(spec)
        print(f"  OK — {len(extraction.get('rules', []))} rules extracted")

    print(f"\nGeneration complete: {len(valid_samples)} valid, {len(failed_specs)} failed")

    if not valid_samples:
        print("ERROR: No valid samples generated")
        sys.exit(1)

    if failed_specs:
        print(f"\nRetrying {len(failed_specs)} failures...")
        for spec in failed_specs:
            prompt = build_prompt(spec)
            try:
                text = generate_single(client, args.model, prompt)
                policy_text, extraction, err = parse_response(text)
                if err:
                    continue
                errors = validate_sample(policy_text, extraction, schema)
                if errors:
                    continue
                valid_samples.append(to_mistral_format(policy_text, extraction))
                valid_specs.append(spec)
                print(f"  Retry OK: {spec['id']}")
            except Exception:
                pass
        print(f"After retries: {len(valid_samples)} valid, {len(specs) - len(valid_samples)} still failed")

    out = Path(args.output_dir)
    if len(valid_samples) >= 10:
        train_n = int(len(valid_samples) * 0.8)
        test_n = int(len(valid_samples) * 0.1)
        val_n = len(valid_samples) - train_n - test_n
        train, val, test = stratified_split(
            valid_samples, valid_specs, train_n, val_n, test_n, args.seed
        )
        write_jsonl(out / "train.jsonl", train)
        write_jsonl(out / "val.jsonl", val)
        write_jsonl(out / "test.jsonl", test)
    else:
        # For dry runs, just write all to train
        write_jsonl(out / "train.jsonl", valid_samples)

    all_rule_types = Counter()
    for sample in valid_samples:
        assistant_content = None
        for msg in sample["messages"]:
            if msg["role"] == "assistant":
                assistant_content = msg["content"]
                break
        if assistant_content:
            parsed = json.loads(assistant_content)
            for rule in parsed.get("rules", []):
                all_rule_types[rule.get("rule_type", "unknown")] += 1

    print(f"\nFinal rule_type distribution: {dict(all_rule_types.most_common())}")
    print("Done!")


if __name__ == "__main__":
    main()
