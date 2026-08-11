# System Architecture

```
                     ┌─────────────────────────┐
                     │   Evaluation Input       │
                     │   (Flask form / CSV /    │
                     │    API)                  │
                     │  question, response,     │
                     │  optional reference      │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  Orchestration Layer     │
                     │  (ResponseEvaluator)     │
                     └─┬─────┬─────┬─────┬──────┘
                       │     │     │     │
        ┌──────────────┘     │     │     └──────────────┐
        ▼                    ▼     ▼                     ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐
│ Relevance     │ │ Accuracy      │ │ Completeness  │ │ Hallucination     │
│ Judge Agent   │ │ Judge Agent   │ │ Judge Agent   │ │ Judge Agent       │
│ (question vs  │ │ (response vs  │ │ (response vs  │ │ (response vs RAG  │
│  response     │ │  reference +  │ │  question     │ │  retrieved        │
│  only)        │ │  RAG evidence)│ │  aspects +    │ │  evidence)        │
│               │ │               │ │  RAG evidence)│ │                   │
└───────────────┘ └──────┬────────┘ └──────┬────────┘ └────────┬──────────┘
                         │                 │                   │
                         ▼                 ▼                   ▼
                  ┌──────────────────────────────────────────────────┐
                  │              RAG Retrieval Module                 │
                  │     chunk_text() → embed() → FAISS search         │
                  └──────────────────────┬───────────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────────┐
                  │      Reference Knowledge Base (FAISS index)       │
                  │      built from TruthfulQA + SQuAD                 │
                  └──────────────────────────────────────────────────┘

                                  │
              (four dimension scores + reasoning)
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │   Verdict Agent          │
                     │   weighted_score =       │
                     │   0.35*accuracy +        │
                     │   0.30*hallucination +   │
                     │   0.20*completeness +    │
                     │   0.15*relevance         │
                     │   → Pass / Needs         │
                     │     Improvement / Fail   │
                     │   + consolidated summary │
                     └────────────┬─────────────┘
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  Results Display /       │
                     │  Batch Table /           │
                     │  Validation Report       │
                     └─────────────────────────┘
```

## Agent Responsibilities

| Agent | Input | Output | Responsibility |
|---|---|---|---|
| Relevance Judge | question, response | `{score, reason}` | Does the response address what was asked? |
| Accuracy Judge | question, response, reference, retrieved context | `{score, evidence, retrieved_context}` | Is the response factually correct vs reference/RAG evidence? |
| Completeness Judge | question, response, reference, retrieved context | `{score, missing_aspects[], reason, retrieved_context}` | Does the response cover every aspect the question asks for? |
| Hallucination Judge | question, response, retrieved context | `{score, unsupported_claims[], reason, retrieved_context}` | Which specific claims are unsupported by grounding evidence? |
| Verdict Agent | outputs of all 4 judges | `{overall_score, verdict, weights, summary}` | Weighted aggregation into one score + Pass/Needs Improvement/Fail verdict + consolidated reasoning |

## Scoring Model

The Verdict Agent computes a weighted overall score (deterministically, in Python) and maps it to a verdict band:

| Dimension | Weight | Verdict band | Range |
|---|---|---|---|
| Accuracy | 35% | Pass | ≥ 8.0 |
| Hallucination | 30% | Needs Improvement | 5.0 – 7.9 |
| Completeness | 20% | Fail | < 5.0 |
| Relevance | 15% | | |

The two truth-related dimensions (Accuracy + Hallucination) carry 65% combined. The weighted score is always reproducible; the LLM writes only the human-readable summary, with a deterministic fallback if that call fails.

## Orchestration Flow
1. User submits a question + response (+ optional reference) via the web form, or uploads a CSV of pairs for batch evaluation.
2. `ResponseEvaluator.evaluate()` validates input, then calls each of the four judge agents independently (agents don't depend on each other's output — they run as isolated judges, matching the TruLens "feedback function" pattern). Each agent is error-isolated, so one failing agent degrades that dimension rather than crashing the evaluation.
3. Accuracy, Completeness, and Hallucination agents each independently query the RAG retrieval module for supporting context.
4. Each agent prompts Gemini with a strict JSON-only instruction and parses the result defensively (`parse_json_response`), so a malformed LLM response never crashes the app.
5. The four dimension scores pass to the Verdict Agent, which computes the weighted `overall_score`, assigns a verdict, and produces a consolidated reasoning summary.
6. Results are returned to the single-evaluation template, the batch results table, or the validation report.

## Data Models

```python
Submission = {
  "question": str,
  "response": str,
  "reference": str | None,
}

AgentResult = {
  "score": float,        # 1-10
  "reason" | "evidence": str,
  "missing_aspects": list[str] | None,      # completeness agent only
  "unsupported_claims": list[str] | None,   # hallucination agent only
  "retrieved_context": str | None,           # accuracy/completeness/hallucination
}

EvaluationResult = {
  "relevance": AgentResult,
  "accuracy": AgentResult,
  "completeness": AgentResult,
  "hallucination": AgentResult,
  "overall_score": float,    # weighted
  "verdict": str,            # "Pass" | "Needs Improvement" | "Fail"
  "summary": str,            # consolidated reasoning
}
```