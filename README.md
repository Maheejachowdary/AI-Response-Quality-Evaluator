# AI Response Quality Evaluator

A multi-agent system that evaluates AI-generated answers across three
dimensions — **Relevance**, **Accuracy**, and **Hallucination** — using
Google Gemini as the judge LLM, grounded by a RAG pipeline built from
the TruthfulQA and SQuAD benchmark datasets.

See `docs/` for full system design, tech stack, and research notes.
See the setup guide provided alongside this project for exact
installation steps on a fresh machine.

## Quick Start (after venv + pip install are done)
```bash
# 1. Build the RAG knowledge base (one-time, ~2-5 min)
python src/knowledge_base/build_index.py

# 2. Run the web app
python src/app.py
# then open http://127.0.0.1:5000

# 3. Run Milestone 2 validation (3 judge agents on TruthfulQA)
python src/validation/validator.py
```

## Project Structure
```
AI-Response-Quality-Evaluator/
├── requirements.txt
├── .env.example
├── docs/                     # design docs, research, tech stack, milestone reports
└── src/
    ├── app.py                # Flask entry point
    ├── agents/                # Milestone 2: judge agents
    ├── backend/               # LLM wrapper, RAG retrieval, evaluator orchestration
    ├── knowledge_base/        # Milestone 1: builds the FAISS vector index
    ├── validation/            # Milestone 2: validation pipeline + reports
    ├── templates/, static/    # Flask front-end
```
