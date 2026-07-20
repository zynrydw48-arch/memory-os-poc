import numpy as np
from sentence_transformers import SentenceTransformer

from memoryos.embeddings.provider import EmbeddingProvider

# Multilingual (50+ languages incl. Hebrew) -- plain English-only MiniLM was
# measured to fail badly on this corpus's large Hebrew PDF/PPTX share (a
# Hebrew presentation about Israel's 70th anniversary ranked 78th/131 for a
# matching Hebrew query, and missed entirely for the English phrasing).
# The smaller multilingual-MiniLM-L12 fixed Hebrew but measurably regressed a
# few English document queries (e.g. "world map" dropped from rank 1 to rank
# 10); the larger mpnet variant recovered those while keeping Hebrew strong.
DEFAULT_MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        if hasattr(self._model, "get_embedding_dimension"):
            self._dimension = self._model.get_embedding_dimension()
        else:
            self._dimension = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def encode(self, texts: list[str]) -> np.ndarray:
        embeddings = self._model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True
        )
        return embeddings.astype(np.float32)
