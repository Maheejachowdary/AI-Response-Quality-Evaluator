# Milestone 3 Submission Report

**Project:** AI Response Quality Evaluator
**Milestone:** 3

## 1. Deliverables Completed

### 1.1 Completeness Judge Agent
- File: `src/agents/completeness_agent.py`
- Assesses whether the AI response addresses every distinct aspect the question asks for. Breaks the question into its required sub-parts, checks coverage of each, and lists specific omissions with reasoning.
- Scoped to coverage only — independent of accuracy (factual correctness) and relevance (on-topic-ness). A response can be correct and on-topic yet still incomplete.
- RAG-grounded like the Accuracy and Hallucination agents: retrieves source chunks to inform what a full answer would include, but treats them as a guide rather than a checklist.
- Returns `{score, missing_aspects: [...], reason, retrieved_context}`.

### 1.2 Verdict Agent
- File: `src/agents/verdict_agent.py`
- Aggregates the four dimension scores into a single weighted overall score, maps it to a Pass / Needs Improvement / Fail verdict, and produces a consolidated reasoning paragraph.
- **Weighted scoring model:** Accuracy 35%, Hallucination 30%, Completeness 20%, Relevance 15%. The two truth-related dimensions (Accuracy + Hallucination) carry 65% combined, reflecting that a QA tool's primary job is catching wrong and fabricated content.
- **Thresholds:** Pass ≥ 8.0, Needs Improvement 5.0–7.9, Fail < 5.0.
- **Deterministic score, LLM summary.** The weighted score and verdict are computed in Python, so the number is always reproducible. The LLM is used only to write the human-readable reasoning summary, with a deterministic fallback (naming strongest/weakest dimensions, missing aspects, and unsupported-claim count) so the verdict never depends on the LLM call succeeding.
- Returns `{overall_score, verdict, weights, summary}`.

### 1.3 Per-Dimension Evaluation Results Interface
- Files: `src/templates/index.html`, `src/static/css/style.css`
- Displays all required components for a single submission: Question, AI Response, Relevance score + reasoning, Accuracy score + evidence, Completeness score + reasoning, Hallucination score + flagged claims, Overall Score, Final Verdict, and Consolidated Reasoning.
- Each dimension renders as a card with a score bar and its per-evaluation reasoning. Missing aspects and flagged hallucinations render as itemised lists; the verdict panel is colour-coded by outcome.

### 1.4 Batch Evaluation Module
- Files: `src/app.py` (`/batch` route), `src/templates/batch.html`
- User uploads a CSV of question/answer pairs; the system evaluates every row through all four agents and the verdict, then displays aggregated results.
- **Aggregated output:** average score per dimension, average overall, verdict distribution (Pass / Needs Improvement / Fail counts), and a per-row table showing all four dimension scores, overall score, and a colour-coded verdict pill.
- **Robustness:** required-column validation (`question`, `response`; optional `reference`), UTF-8-with-BOM handling, tolerant lowercase column matching, per-row error isolation (a failing row is marked "Error" without aborting the batch), rate limiting between rows, and a 50-row safety cap so a large upload cannot exhaust the daily quota in one submission.

## 2. Orchestration Changes
- File: `src/backend/evaluator.py`
- Extended from three judges to four judges plus the Verdict Agent. Each agent runs independently and is wrapped in its own error handler, so one agent failing degrades that dimension to a zero score rather than crashing the evaluation.
- The overall score now comes from the Verdict Agent's weighted model rather than a plain three-way average.
- The empty-input guard returns the full four-dimension shape plus verdict, so the interface never encounters a missing key.

## 3. How Validation Was Run
- **Dataset:** TruthfulQA (5 seeded misconception/science/history questions in `truthfulqa.json`)
- **Sample size:** 5 (`strategy="all"` — the full available set)
- **Judge/generation model:** `gemini-3.5-flash-lite`
- **Rate limiting:** 8-second delay after response generation and 15-second delay between samples (see §5.1 for why this was raised from Milestone 2's 4 seconds)
- **Output report:** `src/validation/reports/truthfulqa_20260730_002901.txt`
- **Result:** 5/5 samples completed successfully, 0 failures, no quota errors

## 4. Scoring Consistency Findings

### 4.1 Validation set (TruthfulQA, 5 samples)

| Metric | Average |
|---|---|
| Relevance | 10.00 / 10 |
| Accuracy | 10.00 / 10 |
| Completeness | 10.00 / 10 |
| Hallucination | 10.00 / 10 |
| Overall (weighted) | 10.00 / 10 |

Verdict distribution: Pass 5, Needs Improvement 0, Fail 0.

All five samples scored a flat 10.00. As noted in the Milestone 2 report, these TruthfulQA items are well-known misconceptions the generating model handles reliably, so the judges have nothing to mark down. This confirms scoring *consistency* on clean inputs but, on its own, does not demonstrate that the agents can assign *low* scores. That is addressed by the discrimination test below.

### 4.2 Discrimination test (batch module, hand-built CSV)

To test whether the system can fail a bad answer — the gap flagged in Milestone 2's limitations — a two-row CSV was run through the batch module: one correct answer and one deliberately off-topic answer (a description of the Great Wall of China given in reply to "Why is the sky blue?").

| Row | Question | Rel | Acc | Comp | Hall | Overall | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | Do we only use 10% of our brains? | 10 | 10 | 10 | 10 | 10.00 | Pass |
| 2 | Why is the sky blue? | 1 | 1 | 1 | 1 | 1.00 | Fail |

The off-topic response was correctly scored 1/10 across every dimension and returned a Fail verdict. This demonstrates that the low scores and the Fail band of the verdict model are reachable and behave correctly — the discrimination the flat-10 validation set could not show.

## 5. Issues Identified and Resolved During Milestone 3

**5.1 — Per-minute rate limit tripped by the added agents**

Milestone 3 raises the number of API calls per validation sample from four to six (response generation + four judges + verdict summary). During the first Milestone 3 validation run, Sample 3 hit an HTTP 429 error against the `GenerateRequestsPerMinutePerProjectPerModel` quota (limit 15/minute), and the Completeness agent for that sample fell back to a zero score.

Notably, the run still reported "5/5 succeeded" — the per-agent and per-sample error isolation built in Milestone 2 prevented a crash, but it also meant a corrupted dimension score could slip through under an otherwise-clean summary. This is a useful reminder that "no crash" is not the same as "no error."

*Fix:* the inter-sample delay in `validator.py` was raised from 4 to 15 seconds, and the post-generation delay from 4 to 8 seconds, spreading the six calls per sample below the 15-per-minute ceiling. The re-run completed 5/5 with no agent errors and no 429s. The per-minute limit (distinct from the daily limit that caused problems in Milestone 2) is the practical constraint on scaling the agent count on the free tier.

**5.2 — Verdict-summary key contract**

The Verdict Agent returns its reasoning paragraph under the key `summary`, and the interface and validation report were aligned to read that same key, so the consolidated reasoning renders correctly on the single-evaluation page, in the batch view, and in the text report.

## 6. Known Limitations

- **Sample size and flat scores.** The validation set remains 5 hand-authored items, all of which the model answers well, producing a flat 10.00 across dimensions. The batch discrimination test (§4.2) partially offsets this, but a larger benchmark including intentionally weak, partial, and off-topic responses is still needed for statistically meaningful, discriminating averages.
- **Self-evaluation bias.** As in Milestone 2, the same model family (`gemini-3.5-flash-lite`) both generates and judges the responses. The flat 10.00 validation average should be read with this in mind.
- **Completeness on single-part questions.** All five validation questions are single-aspect, so the Completeness agent's core value — detecting partial answers to multi-part questions — is not exercised by the validation set. It was confirmed working on multi-part inputs during development but would benefit from multi-aspect benchmark items.
- **Free-tier throughput.** The 15-requests-per-minute limit makes batch evaluation of large CSVs slow (roughly one row every 20–25 seconds). The 50-row cap is a deliberate guard rather than a true capacity.
- **Retrieval quality unmeasured.** The RAG pipeline's retrieval precision is still not evaluated independently of judge scoring.

## 7. Next Steps

- Expand `truthfulqa.json` to 20+ items including multi-part questions and deliberately weak/off-topic responses, so both the discrimination and the Completeness agent are exercised under validation.
- Decouple the generating model from the judging model to address self-evaluation bias.
- Evaluate RAG retrieval precision independently.
- Consider a paid tier or request batching to remove the per-minute throughput constraint for larger batch runs.