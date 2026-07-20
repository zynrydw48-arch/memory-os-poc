"""Dominant color extraction. Deliberately not ML: bucket pixels into coarse
RGB bins, take the most frequent bins, and map each to the nearest name in a
small named-color table."""

import numpy as np
from PIL import Image

NAMED_COLORS = {
    "black": (20, 20, 20),
    "white": (245, 245, 245),
    "gray": (128, 128, 128),
    "red": (210, 30, 30),
    "orange": (255, 140, 0),
    "yellow": (230, 220, 20),
    "green": (30, 140, 30),
    "blue": (30, 80, 200),
    "purple": (130, 40, 150),
    "pink": (240, 150, 180),
    "brown": (120, 70, 40),
    "beige": (220, 200, 170),
    "cyan": (30, 180, 190),
    "gold": (200, 160, 30),
    "silver": (190, 190, 190),
    "navy": (20, 30, 90),
    "teal": (10, 110, 110),
    "maroon": (110, 20, 30),
    "olive": (110, 110, 20),
}

_NAMES = list(NAMED_COLORS.keys())
_REFS = np.array(list(NAMED_COLORS.values()), dtype=np.float32)

BUCKET_SIZE = 32


def _nearest_color_names(rgb_bins: np.ndarray) -> list[str]:
    # rgb_bins: (N, 3). Distance to every reference color, vectorized.
    dists = ((rgb_bins[:, None, :] - _REFS[None, :, :]) ** 2).sum(axis=2)
    nearest = dists.argmin(axis=1)
    return [_NAMES[i] for i in nearest]


def extract_dominant_colors(image: Image.Image, top_k: int = 3) -> list[str]:
    small = image.convert("RGB").resize((64, 64))
    pixels = np.array(small).reshape(-1, 3).astype(np.int32)

    bucketed = (pixels // BUCKET_SIZE) * BUCKET_SIZE + BUCKET_SIZE // 2
    uniques, counts = np.unique(bucketed, axis=0, return_counts=True)
    order = np.argsort(-counts)

    names_in_order = _nearest_color_names(uniques[order].astype(np.float32))
    result = []
    for name in names_in_order:
        if name not in result:
            result.append(name)
        if len(result) >= top_k:
            break
    return result
