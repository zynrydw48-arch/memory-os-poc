"""Builds a human-readable, non-hallucinated explanation of why a result
matched -- every reason is a direct read of stored metadata, never invented.

Works against either the legacy JSON/NumPy IndexRecord or the SQLite
FileRecord: both share the same file_type/metadata shape, expressed here as
a Protocol so this module doesn't need to depend on either concrete class.
"""

import re
from typing import Protocol

STOPWORDS = {
    "a",
    "an",
    "the",
    "of",
    "in",
    "on",
    "at",
    "for",
    "with",
    "and",
    "or",
    "is",
    "are",
    "this",
    "that",
    "image",
    "picture",
    "photo",
    "document",
    "file",
    "about",
}

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")


class RankedRecord(Protocol):
    file_type: str
    metadata: dict


def _collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def tokenize(query: str) -> list[str]:
    words = [w.lower() for w in _WORD_RE.findall(query)]
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


def build_reasons(query: str, record: RankedRecord) -> list[str]:
    tokens = tokenize(query)
    meta = record.metadata
    reasons = []

    ocr_text = meta.get("ocr_text", "")
    ocr_matches = [t for t in tokens if t in ocr_text.lower()]
    if ocr_matches:
        reasons.append(f"OCR text matches: {', '.join(sorted(set(ocr_matches)))}")

    tag_matches = [tag for tag in meta.get("tags", []) if any(t in tag.lower() for t in tokens)]
    if tag_matches:
        reasons.append(f"Detected tag matches: {', '.join(sorted(set(tag_matches)))}")

    text_snippet = meta.get("text_snippet", "")
    if record.file_type != "image":
        text_matches = [t for t in tokens if t in text_snippet.lower()]
        if text_matches:
            reasons.append(f"Document text matches: {', '.join(sorted(set(text_matches)))}")

    if meta.get("caption"):
        reasons.append(f"Scene caption: {meta['caption']}")
    if meta.get("colors"):
        reasons.append(f"Dominant colors: {', '.join(meta['colors'])}")

    if not reasons:
        reasons.append("Matched by overall semantic similarity (no exact keyword overlap)")
        if text_snippet:
            reasons.append(f"Excerpt: {_collapse_whitespace(text_snippet)[:150]}")

    return reasons
