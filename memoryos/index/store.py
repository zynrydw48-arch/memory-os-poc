"""Lightweight local index: a JSON record list + a row-aligned numpy matrix.

No FAISS, no database. At PoC scale (hundreds to low thousands of files) a
brute-force cosine similarity scan over a numpy array is simpler, easier to
inspect, and fast enough -- pulling in a vector database would be solving a
problem this project doesn't have.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class IndexRecord:
    id: str
    path: str
    filename: str
    extension: str
    file_type: str
    semantic_text: str
    metadata: dict = field(default_factory=dict)
    mtime: float = 0.0
    indexed_at: float = 0.0


class IndexStore:
    """Records and their embeddings, aligned by list position (row i <-> records[i])."""

    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.records_path = self.index_dir / "records.json"
        self.embeddings_path = self.index_dir / "embeddings.npy"
        self.manifest_path = self.index_dir / "manifest.json"
        self.records: list[IndexRecord] = []
        self.embeddings: np.ndarray | None = None
        self._path_to_position: dict[str, int] = {}

    def load(self, embedding_model_name: str | None = None) -> None:
        """Load records/embeddings. If embedding_model_name is given and doesn't
        match the model the on-disk index was built with, the whole index is
        discarded -- embeddings from different models live in incompatible
        vector spaces and must never be mixed or compared."""
        if self.records_path.exists():
            raw = json.loads(self.records_path.read_text(encoding="utf-8"))
            self.records = [IndexRecord(**r) for r in raw]
        else:
            self.records = []

        if self.embeddings_path.exists() and self.records:
            self.embeddings = np.load(self.embeddings_path)
        else:
            self.embeddings = None

        self._rebuild_path_index()

        if embedding_model_name is not None:
            stored_model_name = None
            if self.manifest_path.exists():
                stored_model_name = json.loads(
                    self.manifest_path.read_text(encoding="utf-8")
                ).get("embedding_model_name")
            if stored_model_name != embedding_model_name:
                self.records = []
                self.embeddings = None
                self._rebuild_path_index()
            self._embedding_model_name = embedding_model_name

    def save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.records_path.write_text(
            json.dumps([asdict(r) for r in self.records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if self.embeddings is not None:
            np.save(self.embeddings_path, self.embeddings)
        if getattr(self, "_embedding_model_name", None) is not None:
            self.manifest_path.write_text(
                json.dumps({"embedding_model_name": self._embedding_model_name}),
                encoding="utf-8",
            )

    def _rebuild_path_index(self) -> None:
        self._path_to_position = {r.path: i for i, r in enumerate(self.records)}

    def get_by_path(self, path: str) -> IndexRecord | None:
        position = self._path_to_position.get(path)
        return self.records[position] if position is not None else None

    def upsert(self, record: IndexRecord, embedding: np.ndarray) -> None:
        embedding = embedding.reshape(1, -1).astype(np.float32)
        position = self._path_to_position.get(record.path)

        if position is not None:
            self.records[position] = record
            self.embeddings[position : position + 1] = embedding
        else:
            self.records.append(record)
            if self.embeddings is None:
                self.embeddings = embedding
            else:
                self.embeddings = np.vstack([self.embeddings, embedding])
            self._path_to_position[record.path] = len(self.records) - 1

    def prune_missing(self, existing_paths: set[str]) -> int:
        """Drop records whose source file no longer exists. Returns count removed."""
        keep_positions = [
            i for i, r in enumerate(self.records) if r.path in existing_paths
        ]
        removed = len(self.records) - len(keep_positions)
        self.records = [self.records[i] for i in keep_positions]
        if self.embeddings is not None and keep_positions:
            self.embeddings = self.embeddings[keep_positions]
        elif not keep_positions:
            self.embeddings = None
        self._rebuild_path_index()
        return removed

    def __len__(self) -> int:
        return len(self.records)
