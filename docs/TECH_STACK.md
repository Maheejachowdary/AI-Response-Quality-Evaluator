# Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Web framework | Flask | Lightweight, easy single-page submission form + REST-style `/evaluate` endpoint |
| Judge LLM | Google Gemini (`gemini-2.5-flash`) | Free tier, fast, strong instruction-following for strict JSON output |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | Small, fast, CPU-friendly model good enough for semantic retrieval |
| Vector store | FAISS (`faiss-cpu`) | Industry-standard local vector index, no external DB server needed |
| Benchmark datasets | Hugging Face `datasets` — TruthfulQA, SQuAD | Standard public QA benchmarks used by RAGAS/TruLens-style evaluations |
| Data handling | pandas, numpy | Dataset preprocessing and chunk/embedding manipulation |
| Config | python-dotenv | Keeps the Gemini API key out of source control |

## Why not RAGAS / TruLens directly?
Both were studied during Milestone 1 research. RAGAS's built-in metrics
(faithfulness, answer relevancy, context precision) and TruLens's
feedback-function pattern directly inspired this project's three-agent
design (Relevance / Accuracy / Hallucination), but we implement our own
lightweight agents so each one can return **structured, per-dimension
reasoning** (a `reason`/`evidence` field) rather than a single opaque
metric number — this was a specific project requirement.
