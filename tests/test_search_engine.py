"""Bug-fix regression test: a query like "white dog" must not rank a brown
dog image above a white dog image just because raw cosine similarity (over
the flattened caption/tags/colors text embedding -- see
memoryos/ranking/attribute_boost.py) happened to score the brown dog
slightly higher. DatabaseSearchEngine.search should widen its candidate
pool and let an exact color/object keyword match correct the order.
"""

import sys

import numpy as np

from memoryos.database.db import Database, FileRecord
from memoryos.search.engine import DatabaseSearchEngine

EMBED_DIM = 2


class FakeEmbeddingProvider:
    """Always returns the same fixed query vector -- the test controls the
    file embeddings directly via Database.upsert_file, so only the query
    side needs to be deterministic."""

    @property
    def dimension(self) -> int:
        return EMBED_DIM

    @property
    def model_name(self) -> str:
        return "fake"

    def encode(self, texts):
        return np.tile(np.array([1.0, 0.0], dtype=np.float32), (len(texts), 1))


def _normalize(vector: np.ndarray) -> np.ndarray:
    return vector / np.linalg.norm(vector)


def test_white_dog_query_ranks_white_dog_above_higher_raw_similarity_brown_dog(tmp_path):
    database = Database(tmp_path / "test.sqlite3")

    # Brown dog: closer raw angle to the query vector than the white dog --
    # mirrors the reported bug where a brown dog outscored a white dog on
    # pure embedding similarity alone.
    brown_dog_embedding = _normalize(np.array([0.99, 0.15], dtype=np.float32))
    white_dog_embedding = _normalize(np.array([0.97, 0.2], dtype=np.float32))
    assert brown_dog_embedding[0] > white_dog_embedding[0]  # sanity: brown scores higher raw

    database.upsert_file(
        FileRecord(
            id="brown",
            path="/photos/brown_dog.jpg",
            filename="brown_dog.jpg",
            extension=".jpg",
            file_type="image",
            semantic_text="Scene: a dog sitting outside. Dominant colors: brown, beige.",
            metadata={"colors": ["brown", "beige"], "caption": "a dog sitting outside", "tags": []},
        ),
        brown_dog_embedding,
    )
    database.upsert_file(
        FileRecord(
            id="white",
            path="/photos/white_dog.jpg",
            filename="white_dog.jpg",
            extension=".jpg",
            file_type="image",
            semantic_text="Scene: a dog sitting outside. Dominant colors: white, gray.",
            metadata={"colors": ["white", "gray"], "caption": "a dog sitting outside", "tags": []},
        ),
        white_dog_embedding,
    )

    engine = DatabaseSearchEngine(FakeEmbeddingProvider(), database)
    hits = engine.search("white dog", top_k=2)

    assert hits[0].filename == "white_dog.jpg"
    assert hits[1].filename == "brown_dog.jpg"

    database.close()


def test_search_with_no_attribute_words_keeps_raw_similarity_order(tmp_path):
    database = Database(tmp_path / "test.sqlite3")

    higher_embedding = _normalize(np.array([0.99, 0.15], dtype=np.float32))
    lower_embedding = _normalize(np.array([0.97, 0.2], dtype=np.float32))

    database.upsert_file(
        FileRecord(
            id="a",
            path="/docs/a.pdf",
            filename="a.pdf",
            extension=".pdf",
            file_type="pdf",
            semantic_text="quarterly financial report",
            metadata={"text_snippet": "quarterly financial report"},
        ),
        higher_embedding,
    )
    database.upsert_file(
        FileRecord(
            id="b",
            path="/docs/b.pdf",
            filename="b.pdf",
            extension=".pdf",
            file_type="pdf",
            semantic_text="quarterly financial summary",
            metadata={"text_snippet": "quarterly financial summary"},
        ),
        lower_embedding,
    )

    engine = DatabaseSearchEngine(FakeEmbeddingProvider(), database)
    hits = engine.search("xyz", top_k=2)  # tokenize("xyz") is non-empty but matches nothing

    assert hits[0].filename == "a.pdf"
    assert hits[1].filename == "b.pdf"

    database.close()
