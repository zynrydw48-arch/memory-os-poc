"""Cosine-similarity ranking. Deliberately just numpy over an in-memory matrix
-- at PoC/V1 corpus scale this is simpler and easier to verify than a vector
index library, and the embedding storage behind it is swappable independently
(see memoryos/database/db.py's module docstring)."""

import numpy as np


def rank_by_similarity(
    embeddings: np.ndarray, query_embedding: np.ndarray, top_k: int
) -> list[tuple[int, float]]:
    """Returns up to top_k (row index, similarity) pairs, descending by similarity.
    Assumes embeddings and query_embedding are already L2-normalized, so the dot
    product is the cosine similarity."""
    similarities = embeddings @ query_embedding
    top_k = min(top_k, len(similarities))
    top_indices = np.argsort(-similarities)[:top_k]
    return [(int(idx), float(similarities[idx])) for idx in top_indices]
