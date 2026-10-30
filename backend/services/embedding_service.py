import math
from typing import List, Optional
import ollama

EMBEDDING_MODEL = "nomic-embed-text"

def get_single_embedding(text: str) -> List[float]:
    """
    Computes embedding for a single text using Ollama nomic-embed-text.
    """
    cleaned = text.strip()
    if not cleaned:
        return [0.0] * 768
    # Truncate overly long text chunks to ~2000 chars to avoid memory overload
    if len(cleaned) > 2000:
        cleaned = cleaned[:2000]

    try:
        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=cleaned)
        return response.get("embedding", [])
    except Exception as e:
        print(f"[Warning] Failed to generate embedding with Ollama: {e}")
        return []

def get_batch_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Computes embeddings for a list of texts sequentially or with error recovery.
    """
    embeddings: List[List[float]] = []
    for t in texts:
        emb = get_single_embedding(t)
        embeddings.append(emb)
    return embeddings

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Computes cosine similarity between two float vectors.
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(v1, v2):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a <= 0.0 or norm_b <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
