"""
Milestone 1 deliverable: Reference Knowledge Base builder.

Downloads public QA benchmark data (TruthfulQA, SQuAD) from Hugging Face,
chunks it, generates embeddings, and builds a FAISS vector index on disk.

Run once (and again any time you want to refresh the knowledge base):
    python src/knowledge_base/build_index.py
"""

import os
import pickle
import sys

import faiss
import numpy as np
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.retrieval import chunk_text  # noqa: E402

KB_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(KB_DIR, "kb.index")
CHUNKS_PATH = os.path.join(KB_DIR, "chunks.pkl")

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"


def load_truthfulqa_texts(limit=200):
    print("Downloading TruthfulQA (generation split) from Hugging Face...")
    ds = load_dataset("truthful_qa", "generation", split="validation")
    texts = []
    for row in ds.select(range(min(limit, len(ds)))):
        piece = f"Q: {row['question']}\nA: {row['best_answer']}"
        texts.append(piece)
    print(f"  -> {len(texts)} TruthfulQA records loaded.")
    return texts


def load_squad_texts(limit=300):
    print("Downloading SQuAD from Hugging Face...")
    ds = load_dataset("squad", split="train")
    texts = []
    seen_context = set()
    for row in ds:
        if row["context"] not in seen_context:
            texts.append(row["context"])
            seen_context.add(row["context"])
        if len(texts) >= limit:
            break
    print(f"  -> {len(texts)} unique SQuAD passages loaded.")
    return texts


def build():
    os.makedirs(KB_DIR, exist_ok=True)

    raw_texts = []
    raw_texts.extend(load_truthfulqa_texts())
    raw_texts.extend(load_squad_texts())

    print("\nChunking documents...")
    all_chunks = []
    for text in raw_texts:
        all_chunks.extend(chunk_text(text, chunk_size=150, overlap=30))
    print(f"  -> {len(all_chunks)} chunks created.")

    print(f"\nLoading embedding model: {EMBED_MODEL_NAME} (first run downloads it)...")
    model = SentenceTransformer(EMBED_MODEL_NAME)

    print("Generating embeddings...")
    embeddings = model.encode(
        all_chunks,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    embeddings = np.array(embeddings, dtype="float32")

    print("Building FAISS index (cosine similarity via inner product)...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    faiss.write_index(index, INDEX_PATH)
    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(all_chunks, f)

    print("\nDone.")
    print(f"Index saved to : {INDEX_PATH}")
    print(f"Chunks saved to: {CHUNKS_PATH}")
    print(f"Total chunks   : {len(all_chunks)}")


if __name__ == "__main__":
    build()
