# Redline — Voiceover Script

Total runtime: 76 seconds
Pace: ~140 wpm, measured. Not fast. Let the visuals breathe.

---

## [0:00 — TITLE] 4s

"Redline. An explainable compliance engine for HR policy review."

---

## [0:03 — PROBLEM] 5.7s

"Every time a company updates an HR policy, lawyers spend weeks checking it against California and Federal law — manually, inconsistently, at four hundred dollars an hour."

---

## [0:09 — SAVINGS] 10.3s

"Redline cuts that monthly compliance cost from eighteen thousand dollars to twenty-five hundred — an eighty-six percent reduction.

Review cycles that took two to four weeks now complete in under an hour. And unlike a lawyer, the result is deterministic every time."

---

## [0:18 — PIPELINE] 10s

"Here's how it works. A policy document is uploaded, parsed, and fed to our fine-tuned model, which extracts structured decision rules as JSON.

Those rules are then compared against statute by deterministic code — not another LLM call. The output is an auditable report, ready for a lawyer to spot-check."

---

## [0:28 — FINE-TUNING] 11.5s

"The extraction model is Mistral 7B, fine-tuned with Unsloth QLoRA at four-bit precision on roughly five hundred synthetic policy-to-rule pairs.

Zero-shot Mistral produces zero valid JSON schemas. After fine-tuning, schema validity hits eighty-five percent. Training runs are tracked in Weights and Biases."

---

## [0:39 — INFRA] 9s

"Training runs on an NVIDIA L40S via Hugging Face Jobs — forty-eight gigs of VRAM, LoRA rank sixteen. The adapter is pushed to Hugging Face Hub after each run.

Serving runs separately on an NVIDIA L4 instance on BREV, pulling the adapter at startup."

---

## [0:47 — SERVING] 7s

"Inference uses vLLM with PagedAttention for batching and the outlines library for constrained decoding — so every response is structurally valid JSON before it leaves the model.

Fifty-percentile latency is around three-fifty milliseconds."

---

## [0:54 — SELF-IMPROVEMENT] 12s

"The model improves itself between deploys. Claude Code acts as an agent, using the Weights and Biases MCP server to query eval runs and Weave traces, identify the weakest rule category, generate targeted training pairs for it, trigger a fine-tuning job on Hugging Face, and publish a comparison report — all in one automated loop.

One cycle moved per-type accuracy from eighty-four point eight to ninety-four percent."

---

## [1:05 — TECH STACK] 6s

"The stack: Mistral for the model, NVIDIA BREV for serving, Weights and Biases for experiment tracking and observability, Hugging Face for training and the model registry, vLLM, FastAPI, and Unsloth."

---

## [1:11 — CLOSING] 5s

"Redline. Compliance you can explain."

---

## Recording notes

- Speak each scene's lines so they finish roughly one second before the transition — do not let lines bleed into the next scene.
- "Weights and Biases" not "W and B" on first mention per scene; abbreviate freely after.
- Numbers: say "four hundred dollars" not "$400", "eighty-five percent" not "85%".
- The self-improvement block is the longest single take (12s / ~55 words). Consider a natural breath before "all in one automated loop."
