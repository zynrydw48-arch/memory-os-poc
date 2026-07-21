"""Bug fix: a flattened sentence-transformer embedding of "caption + tags +
colors + OCR text" doesn't reliably bind an adjective to the right noun in
the image it describes -- a caption mentioning "white" for the background
or another object can outscore a photo where the actual subject is white,
so a query like "white dog" can rank a brown dog above a white one on raw
cosine similarity alone. This module re-weights ranking using the same
already-extracted metadata (memoryos/vision/pipeline.py's VisionResult)
that memoryos/ranking/reasons.py already reads for match explanations --
no new extraction, just rewarding records whose stored attributes literally
contain a query's color/object words.

There's no real CLIP (joint image-text embedding) model anywhere in this
codebase -- this boost is a keyword-overlap correction layered on top of
the existing text-embedding similarity, not a replacement for it.
"""

from memoryos.vision.colors import NAMED_COLORS

COLOR_WORDS = frozenset(NAMED_COLORS.keys())

COLOR_MATCH_BOOST = 0.15
OBJECT_MATCH_BOOST = 0.05


def compute_attribute_boost(query_tokens: list[str], metadata: dict) -> float:
    """Returns an additive boost (0.0 if no attribute words match) for a
    record's stored metadata against a tokenized query (see
    memoryos.ranking.reasons.tokenize). Colors get the bigger boost since
    they're matched against a fixed, exact vocabulary (the same one
    memoryos/vision/colors.py extracts against) -- object/tag matches use
    free-form caption/tag text, so they're weighted lower to avoid
    over-trusting a substring match."""
    colors = {c.lower() for c in metadata.get("colors", [])}
    caption_words = set(metadata.get("caption", "").lower().split())
    tag_words = set(" ".join(metadata.get("tags", [])).lower().split())

    boost = 0.0
    for token in query_tokens:
        if token in COLOR_WORDS and token in colors:
            boost += COLOR_MATCH_BOOST
        elif token in caption_words or token in tag_words:
            boost += OBJECT_MATCH_BOOST
    return boost
