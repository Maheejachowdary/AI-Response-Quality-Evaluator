# AI Response Quality Evaluator — Technical Documentation

## 1. Project Overview

The AI Response Quality Evaluator is a multi-agent platform that automatically assesses the quality of AI-generated responses. Given a question and an AI's answer, the system scores the answer across four independent dimensions — Relevance, Accuracy, Completeness, and Hallucination — using a large language model (Google Gemini) as an automated judge (the "LLM-as-judge" pattern). The four scores are combined by a weighted Verdict Agent into a single overall score and a Pass / Needs Improvement / Fail verdict, with a consolidated reasoning summary.

The platform supports single evaluations through a web form, batch evaluation of many question-answer pairs via CSV upload, a statistics dashboard with charts and filters, and downloadable PDF reports. All evaluations are persisted to a database so results can be aggregated, filtered, trended over time, and compared across different AI systems.

## 2. Problem Statement

When an AI system answers a question, there is no automatic way to know whether the answer is good. A response can be fluent and confident yet off-topic, factually wrong, incomplete, or contain fabricated details. Manually reviewing every response does not scale. The problem is compounded by the fact that "quality" is not a single property — an answer can be relevant but inaccurate, or accurate but incomplete. A useful evaluation must therefore measure several distinct dimensions separately and combine them into an actionable verdict.

## 3. Objectives

- Score AI responses on four independent quality dimensions, each with reasoning.
- Ground factual judgments in retrieved evidence rather than the judge model's memory alone (via a RAG knowledge base).
- Aggregate the dimensions into a single weighted verdict that reflects the relative severity of different failure types.
- Support both single and batch (CSV) evaluation.
- Persist results and present them through a dashboard with charts and filters.
- Generate downloadable PDF reports, including improvement recommendations.
- Enable comparison of two or more distinct AI systems on the same set of questions.

## 4. System Architecture

The system is organised in layers: an input layer (web form / CSV / API), an orchestration layer, four independent judge agents, a Verdict Agent, a RAG retrieval module backed by a FAISS knowledge base, a persistence layer, and an output layer (results page, dashboard, PDF report).

Input flows to the orchestrator (`ResponseEvaluator`), which dispatches the same input to all four judges independently — no judge sees another's output, avoiding anchoring. Three of the four judges (Accuracy, Completeness, Hallucination) query the RAG module for grounding evidence; Relevance does not, since it checks only on-topic-ness. The four scores pass to the Verdict Agent, which computes a weighted overall score and verdict. The result is persisted to the database and rendered to the appropriate output surface.

The full architecture diagram and per-agent responsibilities are maintained in `docs/SYSTEM_DESIGN.md`.

## 5. Folder Structure
AI-Response-Quality-Evaluator/
├── src/
│ ├── app.py Flask app: routes for /, /evaluate, /batch, /dashboard, /report
│ ├── agents/
│ │ ├── relevance_agent.py
│ │ ├── accuracy_agent.py
│ │ ├── completeness_agent.py
│ │ ├── hallucination_agent.py
│ │ └── verdict_agent.py
│ ├── backend/
│ │ ├── evaluator.py Orchestration layer (ResponseEvaluator)
│ │ ├── llm.py Gemini API wrapper
│ │ ├── retrieval.py RAG retrieval (embed + FAISS search)
│ │ ├── utils.py JSON parsing, score clamping
│ │ ├── database.py SQLite persistence + dashboard stats
│ │ ├── report_pdf.py PDF report generation (fpdf2)
│ │ └── evaluations.db SQLite database (generated at runtime)
│ ├── knowledge_base/
│ │ ├── build_index.py One-time FAISS index builder
│ │ ├── kb.index FAISS index (generated)
│ │ └── chunks.pkl Chunk store (generated)
│ ├── static/css/style.css
│ ├── templates/
│ │ ├── index.html Single-evaluation page
│ │ ├── batch.html Batch CSV page
│ │ └── dashboard.html Dashboard with charts
│ └── validation/
│ ├── validator.py Milestone validation runner
│ ├── report.py Text report generator
│ ├── dataset_loader.py
│ └── datasets/truthfulqa.json
├── tests/
│ ├── e2e_test.py Offline end-to-end test (mocked LLM)
│ └── consistency_test.py Live scoring-consistency test
└── docs/ Documentation and milestone reports
## 6. Installation Guide

Prerequisites: Python 3.12 (Python 3.14 is incompatible with some dependencies).

1. Clone the repository and enter the project folder.
2. Create and activate a virtual environment:
   - `py -3.12 -m venv venv`
   - Windows PowerShell: `.\venv\Scripts\Activate.ps1`
3. Install dependencies: `python -m pip install -r requirements.txt`
4. Create a `.env` file from `.env.example` and add a Google Gemini API key:
   `GEMINI_API_KEY=your_key_here`
5. Build the knowledge base once: `python src/knowledge_base/build_index.py`
6. Run the app: `python src/app.py` and open `http://127.0.0.1:5000`.

Note: `sentence-transformers` is configured for offline use after the first model download (`HF_HUB_OFFLINE` and `TRANSFORMERS_OFFLINE` are set in `retrieval.py`), so startup does not require network access to Hugging Face.

## 7. API / Route Documentation

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Single-evaluation form |
| `/evaluate` | POST | Evaluate one question/response/reference; stores result; renders scores |
| `/batch` | GET | Batch upload form |
| `/batch` | POST | Evaluate every row of an uploaded CSV; stores each; renders summary + table |
| `/dashboard` | GET | Aggregated statistics and charts; accepts filter query params |
| `/report` | GET | Generates and downloads a PDF report; accepts the same filter params |

Form fields: `/evaluate` accepts `question`, `response`, `reference` (optional), `model_name` (optional). `/batch` accepts `csvfile` (a CSV with `question`, `response`, and optional `reference` columns) and `model_name`.

Filter query parameters (dashboard and report): `model_name`, `dataset`, `mode`, `verdict`, `date_from`, `date_to`.

## 8. Database Schema

SQLite (Python built-in `sqlite3`), one table:
evaluations(
id INTEGER PRIMARY KEY AUTOINCREMENT,
created_at TEXT, -- ISO timestamp
model_name TEXT, -- the AI system that produced the response
dataset TEXT, -- 'manual' | 'batch_csv' | etc.
mode TEXT, -- 'single' | 'batch'
question TEXT,
response TEXT,
reference TEXT,
relevance REAL,
accuracy REAL,
completeness REAL,
hallucination REAL,
overall_score REAL,
verdict TEXT,
hallucination_count INTEGER, -- number of flagged claims
summary TEXT -- consolidated reasoning
)


Access functions in `database.py`: `init_db()`, `save_evaluation(...)`, `fetch_all(filters)`, and `dashboard_stats(filters)`.

## 9. RAG Workflow

The Reference Knowledge Base is built once by `build_index.py`: source records from TruthfulQA and SQuAD are split into overlapping word chunks, each chunk is embedded with the `all-MiniLM-L6-v2` SentenceTransformer model, and the embeddings are stored in a FAISS index (`kb.index`) alongside the chunk text (`chunks.pkl`).

At evaluation time, `retrieval.py` embeds the query with the same model, searches the FAISS index for the most similar chunks (cosine similarity on normalised vectors), and returns them as grounding evidence. Retrieval matches on semantic meaning rather than keyword overlap. The Accuracy, Completeness, and Hallucination agents each call retrieval independently; the Relevance agent does not, since it evaluates on-topic-ness rather than factual grounding.

## 10. Agent Descriptions

- **Relevance Judge** (`relevance_agent.py`): scores whether the response addresses the question, independent of correctness. Input: question, response. Output: `{score, reason}`.
- **Accuracy Judge** (`accuracy_agent.py`): scores factual correctness against the reference answer and retrieved evidence. Output: `{score, evidence, retrieved_context}`.
- **Completeness Judge** (`completeness_agent.py`): checks whether every aspect of the question is addressed and lists omissions. Output: `{score, missing_aspects[], reason, retrieved_context}`.
- **Hallucination Judge** (`hallucination_agent.py`): identifies claims not supported by grounding evidence and lists them. Output: `{score, unsupported_claims[], reason, retrieved_context}`.
- **Verdict Agent** (`verdict_agent.py`): computes the weighted overall score (Accuracy 35%, Hallucination 30%, Completeness 20%, Relevance 15%), maps it to Pass (≥ 8.0) / Needs Improvement (5.0–7.9) / Fail (< 5.0), and produces a consolidated reasoning summary. The weighted score is computed deterministically in Python; the LLM only writes the summary, with a deterministic fallback.

All judge agents prompt Gemini for strict JSON and parse it defensively via `parse_json_response`, so malformed model output never crashes the application. Each agent is independently error-isolated in the orchestrator.

## 11. Dashboard

The dashboard (`/dashboard`, `dashboard.html`) reads aggregated statistics from `dashboard_stats()` and renders:

- Stat cards: total evaluations, Pass / Needs Improvement / Fail counts, hallucination frequency.
- A verdict-distribution pie chart, an average-dimension-score bar chart, and a quality-trend line chart (Chart.js).
- Filters for model, dataset, mode, and verdict; applying a filter recomputes all statistics and charts.

Filtering by `model_name` enables direct comparison of two AI systems evaluated on the same questions.

## 12. Report Generation

The PDF report (`/report`, `report_pdf.py`, using the pure-Python `fpdf2` library) contains: project details, a summary block (totals, averages, hallucination frequency), and per-evaluation results with dimension scores, flagged hallucinations, verdicts, and automatic improvement recommendations. The report honours the same filters as the dashboard, so a filtered report (e.g. one AI system only) can be downloaded directly.

## 13. Testing Results

**End-to-end testing** (`tests/e2e_test.py`, offline with mocked LLM and retrieval): 26 checks across 9 groups — agent scoring (good and bad responses), invalid/empty input handling, database persistence, dashboard statistics, all Flask routes, batch workflow (valid CSV, missing columns, missing file), PDF generation, and filtered reporting. Result: all checks passed.

**Scoring consistency validation** (`tests/consistency_test.py`, live Gemini API): the 5-sample TruthfulQA set was evaluated 3 times. Average overall-score standard deviation across samples was 0.057, i.e. highly consistent. All five verdicts were stable across runs. 19 of 20 dimension scores were identical across all runs; the single exception was one sample's Hallucination score (values 10, 8, 10), which reflects the finer-grained judgment that agent makes. The verdict was unaffected, showing the weighted model absorbs minor per-dimension variation.

**Two-system comparison**: Gemini and Copilot were each evaluated on the same four general-knowledge questions. Gemini averaged 9.25/10 (3 Pass, 1 Needs Improvement); Copilot averaged 9.85/10 (4 Pass). Both scored 10.00 on Relevance, Accuracy, and Completeness; the difference was entirely in Hallucination (Gemini 7.50, Copilot 9.50), driven by one response where a specific unsupported numeric claim was flagged.

## 14. Limitations

- **Small validation set.** The bundled validation dataset has 5 samples, all of which the judge handles well, producing high, low-variance scores. This demonstrates consistency but not the full discriminating range; the two-system and off-topic tests provide the low-score evidence.
- **Self-evaluation considerations.** Gemini serves as the judge. When it also generates the response under test (in validation), self-preference bias is possible; the two-system comparison mitigates this by judging responses from other systems.
- **Free-tier rate limits.** Each evaluation makes several API calls (four judges plus verdict), and the per-minute free-tier limit (15 requests/minute) constrains batch throughput; delays are inserted between calls.
- **Retrieval precision unmeasured.** The RAG pipeline supplies grounding evidence but its retrieval precision has not been evaluated independently.
- **Judge subjectivity on specific claims.** As the two-system comparison showed, the Hallucination agent penalises specific numeric claims not present in the grounding evidence even when plausibly true, which can vary run to run.

## 15. Future Work

- Expand the validation dataset with multi-part questions and deliberately weak responses.
- Decouple the generating model from the judging model to eliminate self-evaluation bias.
- Evaluate RAG retrieval precision independently.
- Add date-range filtering UI and per-model trend overlays to the dashboard.
- Support additional judge models and let users choose the judge.
- Move batch evaluation to a background queue to handle larger CSVs within rate limits.