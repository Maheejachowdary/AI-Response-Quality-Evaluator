# Milestone 2 Submission Report

**Project:** AI Response Quality Evaluator
**Milestone:** 2
**GitHub Repo:** <paste your repo link here>

## 1. Deliverables Completed

### 1.1 Relevance Judge Agent
- File: `src/agents/relevance_agent.py`
- Scores how directly the AI response addresses the question, on a 1–10 scale, independent of factual correctness.
- Returns `{score, reason}` — reasoning is generated per evaluation by the judge LLM (Gemini), not a static template.

### 1.2 Accuracy Judge Agent
- File: `src/agents/accuracy_agent.py`
- Checks factual correctness against (a) an optional human-provided reference answer and (b) source chunks retrieved from the RAG knowledge base for the question.
- Returns `{score, evidence, retrieved_context}`.

### 1.3 Hallucination Detection Agent
- File: `src/agents/hallucination_agent.py`
- Decomposes the response into factual claims and cross-references each against the RAG-retrieved evidence (+ reference answer if present).
- Returns `{score, unsupported_claims: [...], reason, retrieved_context}` — specific unsupported statements are listed individually, not just summarized.

### 1.4 Validation
- File: `src/validation/validator.py` + `src/validation/dataset_loader.py` + `src/validation/report.py`
- Runs all three agents against sampled Q/A pairs from `truthfulqa.json` (TruthfulQA benchmark).
- Produces a timestamped `.txt` report in `src/validation/reports/` with per-sample scores/reasoning and aggregate averages (mean relevance, accuracy, hallucination, and overall score across the sample).
- Per-sample error isolation: a sample that fails (API error, quota exhaustion, malformed output) is excluded from the report and listed separately, so failed calls never enter the aggregate averages.

## 2. How Validation Was Run
- **Dataset:** TruthfulQA (5 seeded misconception/science/history questions in `truthfulqa.json`)
- **Sample size:** 5 (`strategy="all"` — the full available set)
- **Judge/generation model:** `gemini-3.5-flash-lite`
- **Rate limiting:** 4-second delay between API calls to stay within free-tier quota
- **Output report:** `src/validation/reports/truthfulqa_20260724_010440.txt`
- **Result:** 5/5 samples completed successfully, 0 failures

## 3. Scoring Consistency Findings

| Metric | Average |
|---|---|
| Relevance | 10.00 / 10 |
| Accuracy | 10.00 / 10 |
| Hallucination | 9.20 / 10 |
| Overall | 9.72 / 10 |

Highest overall score: 10.00 — Lowest overall score: 9.30

**Observations:**

- **Relevance** was uniformly 10/10. All five questions are direct factual queries and the generated responses addressed them squarely, so this metric showed no discriminating power on this sample set. A validation set containing deliberately off-topic or evasive responses would be needed to demonstrate that the agent can distinguish relevance levels.
- **Accuracy** was uniformly 10/10, consistent with the reference answers. All five TruthfulQA items are well-known misconceptions the generating model handles reliably.
- **Hallucination** was the only metric producing variation (9.20 average, one sample at 9.30). Four of five samples returned no unsupported claims. The single flagged sample (`tqa_005`, Napoleon's height) surfaced specific figures and named entities absent from the grounding evidence — an autopsy measurement in *pieds du roi*, a conversion to 169 cm, the Duke of Wellington's height, and the Imperial Guard's selection for stature. These are plausible but unverifiable against the retrieved context, which is precisely the category the agent is intended to catch.
- The variation pattern indicates hallucination detection is currently the most informative of the three metrics, since it is the only one sensitive to detail the reference answer does not cover.

## 4. Issues Identified and Resolved During Validation

Three defects were found and fixed during this milestone. The first validation run produced an overall average of 2.00/10, which on inspection reflected system failures rather than response quality.

**4.1 — JSON parsing failure (silent, misattributed)**

`parse_json_response()` in `src/backend/utils.py` used a bare `json.loads()` call. Because `json.loads` is strict, a single character of prose around the JSON object caused a parse failure. The judge LLM frequently appended a closing line such as "Let me know if you need more detail," which was enough to fail the parse. The fallback path then reported this as *"the AI service was unavailable"* — misattributing a local parsing bug to an API outage.

This was diagnosed by noting that on one sample the Accuracy agent scored 10/10 while Relevance and Hallucination both returned the unavailability message, in the same run against the same API — ruling out a service outage.

*Fix:* markdown fence stripping plus regex extraction of the first balanced JSON object from surrounding prose, with the raw model output preserved in the fallback message for future diagnosis.

**4.2 — API errors masquerading as valid responses**

`generate_response()` in `src/backend/llm.py` caught all exceptions and returned `f"ERROR: {e}"` as an ordinary string. A failed call was therefore indistinguishable from a genuine response. When the free-tier daily quota was exhausted, the resulting HTTP 429 error text was stored as the "generated response" and passed to all three judge agents, which dutifully scored it 1/10 — silently corrupting the aggregate averages with measurements of an error message.

*Fix:* `generate_response()` now raises on failure. The validator catches per sample, records the failure, excludes that sample from the report, and prints a success/failure count. When no samples succeed, no report is written at all, preventing a misleading deliverable.

**4.3 — Hallucination agent over-flagging**

After 4.1 and 4.2 were resolved, a clean 5/5 run produced a Hallucination average of 4.20/10. Manual inspection of the flagged claims showed the score was a prompt defect, not a quality signal. The agent was flagging:

- Claims stated almost verbatim in the reference answer (e.g. "Napoleon Bonaparte was not unusually short"; the WWII propaganda origin of the carrot myth)
- Uncontroversial general knowledge (e.g. "Carrots are rich in beta-carotene, which the body converts into Vitamin A")
- Non-claims — rhetorical framing and section headings such as "The short answer is: Probably nothing bad" and "Here is a breakdown of what is actually happening"

The prompt instructed the model to check whether each claim was "supported by the grounding evidence," which it interpreted as requiring verbatim presence in the retrieved chunks. Any response more detailed than the one-sentence reference answer was penalised.

*Fix:* the prompt now defines what constitutes a factual claim (excluding framing and transitions) and explicitly distinguishes *added detail* from *contradiction* — flagging only claims that conflict with the evidence or that assert specific fabricated-looking facts such as names, dates, or figures.

*Effect:* Hallucination average rose from 4.20 to 9.20. Relevance and Accuracy were unchanged at 10.00, confirming the prompt revision was correctly scoped to a single agent.

**4.4 — Supporting environment fixes**

- Model `gemini-2.5-flash-lite` appeared in `list_models()` output but returned HTTP 404 ("no longer available to new users") on invocation, demonstrating that model listings do not reflect per-key availability. Switched to `gemini-3.5-flash-lite`.
- Added `src/backend/__init__.py`, which was missing while sibling packages had one.
- Replaced non-ASCII console output and added `sys.stdout.reconfigure(encoding="utf-8")`, as the Windows cp1252 console raised `UnicodeEncodeError` after a successful evaluation.

## 5. Known Limitations

- **Sample size.** 5 samples is too small for statistically meaningful averages. Results are indicative only. `truthfulqa.json` is hand-authored and should be expanded to 20+ items before the scores are treated as a quality measure.
- **Self-evaluation bias.** The same model family (`gemini-3.5-flash-lite`) both generates the responses under test and judges them. A model is likely to rate its own output favourably, and the 9.72 overall average should be read with that in mind. Evaluating responses from a different model family would give a more credible measure.
- **No discriminating cases.** The validation set contains only questions the generator answers well. Without deliberately poor, off-topic, or fabricated responses in the set, the agents' ability to assign *low* scores correctly remains untested. Relevance and Accuracy at a flat 10.00 reflect this gap.
- **No human-annotated ground truth.** The judge scores themselves have not been validated against human ratings, so agreement between the agents and human judgement is unmeasured.
- **Retrieval quality unmeasured.** The RAG pipeline (592 chunks from TruthfulQA + SQuAD, `all-MiniLM-L6-v2`, FAISS) supplies grounding evidence but its retrieval precision has not been evaluated independently.

## 6. Next Steps for Milestone 3

- Expand `truthfulqa.json` to 20+ items, including intentionally weak responses to test the agents' low-score behaviour.
- Decouple the generating model from the judging model to address self-evaluation bias.
- Build the Completeness Judge Agent and the Verdict Agent.
- Add a dashboard/analytics UI; validation output is currently a plain text report.
- Evaluate retrieval precision independently of judge scoring.