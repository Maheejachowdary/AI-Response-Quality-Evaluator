"""
Reference Knowledge Base + RAG retrieval.

Pipeline:
  1. Text is split into overlapping chunks (chunking).
  2. Each chunk is embedded with a SentenceTransformer model (embedding).
  3. Embeddings are indexed in FAISS for fast similarity search (vector store).
  4. retrieve() embeds a query and returns the top-k most similar chunks,
     which the judge agents use as grounding evidence.

Run `python src/knowledge_base/build_index.py` once before using this
module, to create the FAISS index + chunks.pkl on disk.
"""

import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import pickle

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(BASE_DIR, "knowledge_base")
INDEX_PATH = os.path.join(KB_DIR, "kb.index")
CHUNKS_PATH = os.path.join(KB_DIR, "chunks.pkl")

_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
_model = None
_index = None
_chunks = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(_EMBED_MODEL_NAME)
    return _model


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 40):
    """
    Splits text into overlapping word chunks.
    chunk_size / overlap are word counts, not characters.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def _load_index():
    global _index, _chunks
    if _index is not None and _chunks is not None:
        return

    if not os.path.exists(INDEX_PATH) or not os.path.exists(CHUNKS_PATH):
        raise FileNotFoundError(
            "Knowledge base index not found.\n"
            "Run: python src/knowledge_base/build_index.py"
        )

    _index = faiss.read_index(INDEX_PATH)
    with open(CHUNKS_PATH, "rb") as f:
        _chunks = pickle.load(f)


def retrieve(query: str, k: int = 3):
    """
    Returns the top-k most relevant chunks from the knowledge base
    for a given query string, ranked by cosine similarity.
    """
    _load_index()
    model = _get_model()

    query_vec = model.encode([query], normalize_embeddings=True)
    query_vec = np.array(query_vec, dtype="float32")

    scores, indices = _index.search(query_vec, k)

    results = []
    for idx, score in zip(indices[0], scores[0]):
        if idx == -1:
            continue
        results.append({
            "text": _chunks[idx],
            "similarity": float(score),
        })
    return results


def retrieve_context_text(query: str, k: int = 3) -> str:
    """Convenience helper: returns retrieved chunks joined as one string."""
    hits = retrieve(query, k=k)
    if not hits:
        return ""
    return "\n---\n".join(h["text"] for h in hits)
