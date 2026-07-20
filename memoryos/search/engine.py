import time
from dataclasses import dataclass

from memoryos.database.db import Database
from memoryos.embeddings.provider import EmbeddingProvider
from memoryos.index.store import IndexStore
from memoryos.ranking.reasons import build_reasons
from memoryos.ranking.similarity import rank_by_similarity

DEFAULT_TOP_K = 10


@dataclass
class SearchHit:
    rank: int
    filename: str
    path: str
    similarity: float
    reasons: list[str]


class SearchEngine:
    """Legacy JSON/NumPy-index-backed search, kept working unchanged as a
    verified fallback (used by memoryos/cli/main.py) until the SQLite-backed
    DatabaseSearchEngine below has been fully validated."""

    def __init__(self, embedding_provider: EmbeddingProvider, index_store: IndexStore):
        self._embedding_provider = embedding_provider
        self._index_store = index_store

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[SearchHit]:
        if not self._index_store.records or self._index_store.embeddings is None:
            return []

        query_embedding = self._embedding_provider.encode([query])[0]
        ranked = rank_by_similarity(self._index_store.embeddings, query_embedding, top_k)

        hits = []
        for rank, (idx, similarity) in enumerate(ranked, start=1):
            record = self._index_store.records[idx]
            hits.append(
                SearchHit(
                    rank=rank,
                    filename=record.filename,
                    path=record.path,
                    similarity=similarity,
                    reasons=build_reasons(query, record),
                )
            )
        return hits


class DatabaseSearchEngine:
    """SQLite-backed search for the desktop UI. Same ranking/reason logic as
    SearchEngine (shared via memoryos.ranking), just a different storage
    backend -- this is what the embedding-storage swappability promise looks
    like in practice."""

    def __init__(self, embedding_provider: EmbeddingProvider, database: Database):
        self._embedding_provider = embedding_provider
        self._database = database

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[SearchHit]:
        start = time.time()
        records, embeddings = self._database.embedding_matrix()
        if not records or embeddings is None:
            self._database.record_search(duration_seconds=time.time() - start, result_count=0)
            return []

        query_embedding = self._embedding_provider.encode([query])[0]
        ranked = rank_by_similarity(embeddings, query_embedding, top_k)

        hits = []
        for rank, (idx, similarity) in enumerate(ranked, start=1):
            record = records[idx]
            hits.append(
                SearchHit(
                    rank=rank,
                    filename=record.filename,
                    path=record.path,
                    similarity=similarity,
                    reasons=build_reasons(query, record),
                )
            )

        self._database.record_search(duration_seconds=time.time() - start, result_count=len(hits))
        return hits
