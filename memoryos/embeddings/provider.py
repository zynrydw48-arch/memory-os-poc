"""EmbeddingProvider interface.

The search engine only ever talks to this interface, never to a specific
model. Swapping the text embedding model (MiniLM -> BGE -> E5 -> Jina ->
Nomic -> Qwen, ...) means writing a new class here and nothing else changes.
"""

from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Length of the embedding vectors this provider produces."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifies which model produced these vectors, so a stored index built
        with a different model/vector-space can be detected and never mixed in."""

    @abstractmethod
    def encode(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of strings. Returns a (len(texts), dimension) float32 array,
        L2-normalized so cosine similarity reduces to a dot product."""
