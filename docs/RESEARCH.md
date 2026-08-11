# Research Notes (Milestone 1)

## LLM Evaluation Techniques
- **Reference-based scoring**: compare a model's answer to a known-correct reference (used by our Accuracy agent).
- **Reference-free / self-consistency scoring**: judge quality without ground truth, e.g. relevance-to-question checks (used by our Relevance agent).
- **LLM-as-a-judge**: using a strong LLM (Gemini) to score another model's output on a defined rubric, returning both a score and natural-language reasoning — this is the pattern this project follows throughout.

## Hallucination Detection Methods
- **Claim decomposition**: break a response into individual factual statements, then check each one against source evidence (this is what the Hallucination agent does).
- **Retrieval grounding**: compare claims against retrieved passages from a trusted knowledge base rather than the model's own internal knowledge, which reduces the judge's own hallucination risk.
- **Faithfulness scoring** (as used in RAGAS): the proportion of claims in a response that are supported by retrieved context.

## RAG Architecture
Standard 3-stage pipeline: **chunk → embed → index**, then at query time: **embed query → similarity search → return top-k chunks as context**. This project implements it with `sentence-transformers` (embedding) + FAISS (vector index), following the same shape used by RAGAS's and TruLens's context-retrieval steps.

## Existing Frameworks Studied
- **RAGAS**: provides metrics like faithfulness, answer relevancy, and context precision — directly evaluates RAG pipelines. Inspired our score naming and the idea of per-dimension, RAG-grounded evaluation.
- **TruLens**: introduces the "feedback function" concept — small, independent evaluators that each score one dimension and can be composed. Our three-agent structure (Relevance / Accuracy / Hallucination) mirrors this composability.

## Design Choices Informed by Research
- Each judge is a separate agent/prompt (like TruLens feedback functions) rather than one big prompt, so scores and reasoning stay isolated and debuggable per dimension.
- Accuracy and Hallucination agents both pull RAG-retrieved evidence (RAGAS-style grounding) in addition to any optional human reference answer, so the system still works even when no reference is supplied.
- All judge outputs are forced into strict JSON so they can be parsed defensively and rendered/reported without extra NLP post-processing.
