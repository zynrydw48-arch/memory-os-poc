import numpy as np
import pytest

from memoryos.ranking.reasons import build_reasons, tokenize
from memoryos.ranking.similarity import rank_by_similarity


def _normalize(vectors: np.ndarray) -> np.ndarray:
    return vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)


def test_rank_by_similarity_orders_descending_and_respects_top_k():
    rng = np.random.default_rng(0)
    embeddings = _normalize(rng.random((5, 8)).astype(np.float32))
    query = embeddings[2]  # identical to row 2 -> should rank first with similarity ~1.0

    ranked = rank_by_similarity(embeddings, query, top_k=3)

    assert len(ranked) == 3
    assert ranked[0][0] == 2
    assert ranked[0][1] == pytest.approx(1.0, abs=1e-5)
    similarities = [sim for _, sim in ranked]
    assert similarities == sorted(similarities, reverse=True)


def test_rank_by_similarity_caps_top_k_to_available_rows():
    embeddings = _normalize(np.random.default_rng(1).random((2, 8)).astype(np.float32))
    ranked = rank_by_similarity(embeddings, embeddings[0], top_k=10)
    assert len(ranked) == 2


def test_near_duplicate_sentences_outrank_unrelated_one():
    # Simple bag-of-words style embedding stand-in: three fixed 4-dim vectors
    # where two are "similar" (small angle) and one is "unrelated" (orthogonal).
    dog_beach = np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32)
    dog_park = np.array([0.85, 0.2, 0.0, 0.0], dtype=np.float32)
    financial_report = np.array([0.0, 0.0, 0.9, 0.1], dtype=np.float32)
    embeddings = _normalize(np.vstack([dog_beach, dog_park, financial_report]))
    query = _normalize(np.array([[0.88, 0.15, 0.0, 0.0]], dtype=np.float32))[0]

    ranked = rank_by_similarity(embeddings, query, top_k=3)
    order = [idx for idx, _ in ranked]

    assert order[0] in (0, 1)  # one of the dog vectors is the closest match
    assert order[-1] == 2  # financial_report is the least similar


class _FakeRecord:
    def __init__(self, file_type: str, metadata: dict):
        self.file_type = file_type
        self.metadata = metadata


def test_tokenize_drops_stopwords_and_short_words():
    tokens = tokenize("a photo of the dog on a beach")
    assert "dog" in tokens
    assert "beach" in tokens
    assert "a" not in tokens
    assert "of" not in tokens
    assert "photo" not in tokens  # explicit stopword


def test_build_reasons_surfaces_ocr_and_caption_matches():
    record = _FakeRecord(
        file_type="image",
        metadata={"ocr_text": "Google", "caption": "google logo", "colors": ["white", "red"]},
    )
    reasons = build_reasons("Google logo", record)
    joined = " ".join(reasons)
    assert "google" in joined.lower()
    assert any("OCR" in r for r in reasons)


def test_build_reasons_falls_back_to_semantic_similarity_note_when_no_overlap():
    record = _FakeRecord(file_type="pdf", metadata={"text_snippet": "unrelated content here"})
    reasons = build_reasons("xyz nonexistent query terms", record)
    assert reasons[0] == "Matched by overall semantic similarity (no exact keyword overlap)"
