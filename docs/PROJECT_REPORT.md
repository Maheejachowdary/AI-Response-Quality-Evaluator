# AI Response Quality Evaluator — Project Report

## 1. Introduction

Large language models are now widely used to answer questions, but the quality of their answers varies and is difficult to assess at scale. An answer may be fluent yet off-topic, confident yet factually wrong, or complete-sounding yet missing part of what was asked. Manual review does not scale, and a single "good/bad" label hides the fact that quality has several independent dimensions.

This project presents the AI Response Quality Evaluator: a multi-agent platform that automatically evaluates an AI-generated response against a question, scoring it on four independent dimensions and combining those scores into a single weighted verdict. The platform uses a large language model (Google Gemini) as an automated judge, grounds its factual judgments in a retrieval-augmented knowledge base, persists all results, and presents them through a dashboard and downloadable PDF reports. It also supports comparing two or more AI systems on the same questions.

## 2. Objectives

1. Evaluate AI responses across four independent dimensions — Relevance, Accuracy, Completeness, and Hallucination — each accompanied by generated reasoning.
2. Ground factual judgments in retrieved evidence using a RAG knowledge base rather than the judge model's memory alone.
3. Aggregate the four dimensions into a weighted overall score and a Pass / Needs Improvement / Fail verdict.
4. Provide single and batch (CSV) evaluation modes.
5. Persist results and visualise them through a dashboard with charts and filters.
6. Generate downloadable PDF reports with improvement recommendations.
7. Enable evaluation and comparison of at least two distinct AI systems.

## 3. Methodology

The evaluation follows the "LLM-as-judge" methodology, in which a language model scores another model's output. Rather than asking for a single overall judgment, the system decomposes quality into four separate questions and assigns one specialised judge agent to each. Each agent constructs a focused prompt, requests a strict JSON response from Gemini, and parses it defensively.

Factual judgments are grounded using Retrieval-Augmented Generation. A knowledge base built from the TruthfulQA and SQuAD benchmarks is chunked, embedded with the `all-MiniLM-L6-v2` model, and indexed in FAISS. At evaluation time, the question is embedded and the most semantically similar chunks are retrieved as grounding evidence for the Accuracy, Completeness, and Hallucination agents.

The four dimension scores are combined by a Verdict Agent using a weighted model that reflects the relative severity of failure types: Accuracy 35%, Hallucination 30%, Completeness 20%, Relevance 15%. The two truth-related dimensions carry 65% combined, on the principle that a quality evaluator's primary job is catching wrong or fabricated content. The weighted score is computed deterministically and mapped to a verdict band: Pass ≥ 8.0, Needs Improvement 5.0–7.9, Fail < 5.0.

## 4. System Design

The platform is layered:

- **Input layer:** a Flask web form for single evaluations, a CSV upload for batch evaluation, and route-level API access.
- **Orchestration layer:** `ResponseEvaluator` dispatches input to the four judge agents independently (no agent sees another's output) and passes their scores to the Verdict Agent. Each agent is error-isolated.
- **Judge agents:** Relevance, Accuracy, Completeness, and Hallucination.
- **RAG module:** embeds the query and retrieves grounding evidence from the FAISS knowledge base.
- **Verdict Agent:** weighted aggregation, verdict assignment, and consolidated reasoning.
- **Persistence layer:** a SQLite database storing every evaluation with its scores, verdict, model name, mode, and timestamp.
- **Output layer:** the single-result page, the batch results table, the statistics dashboard, and the PDF report.

The full architecture diagram is provided in `docs/SYSTEM_DESIGN.md`.

## 5. Implementation

The platform is implemented in Python 3.12 with Flask. Key components:

- **Judge agents** (`src/agents/`): each is a class that builds a prompt, calls Gemini via `llm.py`, and returns a parsed result dictionary.
- **Gemini wrapper** (`llm.py`): uses `gemini-3.5-flash-lite`; raises on API failure so that errors are never mistaken for valid responses.
- **Defensive parsing** (`utils.py`): extracts JSON from model output even when wrapped in prose, and clamps scores to the 1–10 range.
- **Retrieval** (`retrieval.py`): SentenceTransformer embeddings + FAISS search, configured for offline model loading.
- **Verdict Agent** (`verdict_agent.py`): deterministic weighted scoring with an LLM-written summary and a deterministic fallback.
- **Persistence** (`database.py`): built-in `sqlite3`; provides save, fetch, and aggregate-statistics functions.
- **Dashboard** (`dashboard.html`): Chart.js pie, bar, and line charts driven by server-computed statistics, with model/dataset/mode/verdict filters.
- **PDF reports** (`report_pdf.py`): the pure-Python `fpdf2` library, chosen to avoid compiled dependencies.

Development proceeded in phases, each verified before the next: persistence, model attribution, dashboard, PDF export, and testing.

## 6. Experimental Results

### 6.1 Scoring consistency

The 5-sample TruthfulQA validation set was evaluated three times using the live Gemini judge. Results:

- Average overall-score standard deviation across samples: **0.057** (highly consistent).
- All five verdicts were **stable** across the three runs.
- 19 of 20 dimension scores were identical across all runs. The single exception was one sample's Hallucination score (values 10, 8, 10, standard deviation 0.94), which slightly moved that sample's overall score (10.0, 9.4, 10.0) without changing its verdict.

This demonstrates that the agents produce stable, reproducible results, and that the weighted verdict model absorbs minor per-dimension variation.

### 6.2 Two-system comparison

Two AI systems, Gemini and Copilot, were evaluated on the same four general-knowledge questions:

| System | Overall | Relevance | Accuracy | Completeness | Hallucination | Verdicts |
|---|---|---|---|---|---|---|
| Gemini | 9.25/10 | 10.00 | 10.00 | 10.00 | 7.50 | 3 Pass, 1 Needs Improvement |
| Copilot | 9.85/10 | 10.00 | 10.00 | 10.00 | 9.50 | 4 Pass |

Both systems answered all four questions correctly, scoring 10.00 on Relevance, Accuracy, and Completeness. The entire difference lay in the Hallucination dimension, concentrated in one question (whether lightning strikes the same place twice). Gemini's answer included a specific numeric claim not present in the grounding evidence, which the Hallucination agent flagged, lowering that response to a Needs Improvement verdict. Copilot's answer to the same question was phrased with less specific, better-hedged detail and was not flagged.

### 6.3 Discrimination

Earlier testing confirmed the system can assign low scores correctly: a deliberately off-topic response (a description of the Great Wall of China given in reply to "Why is the sky blue?") scored 1/10 across all dimensions and received a Fail verdict, with the irrelevant claim flagged as a hallucination.

## 7. Dashboard Screenshots

*(Insert screenshots here.)* The dashboard shows the stat cards (total evaluations, Pass/Needs Improvement/Fail counts, hallucination frequency), the verdict-distribution pie chart, the average-dimension-score bar chart, and the quality-trend line chart. Suggested screenshots: (1) the full dashboard with all evaluations, (2) the dashboard filtered to Gemini, (3) the dashboard filtered to Copilot, showing the difference in the two systems' statistics.

## 8. Evaluation Analysis

The results show that the four-dimension design is the platform's key strength: a single overall score would have rated Gemini and Copilot as near-identical, but decomposing quality revealed that the difference was specifically in hallucination on one factual claim. The finding also surfaced a meaningful property of the Hallucination judge — it scrutinises specific, confident factual claims (particularly numbers and named entities) more heavily than hedged phrasing, even when the claim is plausibly true. This is appropriate behaviour for a quality evaluator whose purpose is to catch potentially fabricated detail, though it introduces the small run-to-run variation observed in the consistency test.

The weighted verdict model behaved as intended: it kept the overall outcome stable when a single dimension fluctuated, and it correctly separated a passing system from one needing improvement based on a real quality difference.

## 9. Testing

Two test suites were implemented:

- **End-to-end test** (`tests/e2e_test.py`), run offline with a mocked LLM and retrieval layer, covering single evaluation, batch evaluation, dashboard statistics, PDF generation, RAG usage, agent scoring, verdict generation, error handling, and invalid input. All 26 checks across 9 groups passed.
- **Consistency validation** (`tests/consistency_test.py`), run against the live Gemini API, measuring score variation across repeated runs (reported in Section 6.1).

Together these cover the full test matrix required: single and batch workflows, dashboard updates, report generation, RAG retrieval, agent scoring, verdict generation, error handling, and invalid-input handling.

## 10. Conclusion

The AI Response Quality Evaluator meets its objectives. It evaluates AI responses across four independent, RAG-grounded dimensions; combines them into a weighted, interpretable verdict; supports single and batch evaluation; persists and visualises results through a filterable dashboard; and produces downloadable PDF reports. Testing confirms the platform is internally consistent (overall-score standard deviation 0.057) and functionally complete (26/26 end-to-end checks passing). The two-system comparison demonstrates the platform's central value: by separating quality into dimensions, it reveals meaningful differences between AI systems that a single score would obscure. Identified limitations — a small validation set, self-evaluation considerations, and free-tier rate limits — define clear directions for future work.