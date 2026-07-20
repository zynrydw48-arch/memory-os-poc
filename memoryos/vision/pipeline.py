import io
from dataclasses import dataclass, field

from PIL import Image

from memoryos.ocr.engine import OcrEngine
from memoryos.vision.caption import Captioner
from memoryos.vision.colors import extract_dominant_colors
from memoryos.vision.tags import ObjectTagger


@dataclass
class VisionResult:
    colors: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    ocr_text: str = ""
    caption: str = ""

    @property
    def semantic_text(self) -> str:
        parts = []
        if self.caption:
            parts.append(f"Scene: {self.caption}.")
        if self.tags:
            parts.append(f"Objects detected: {', '.join(self.tags)}.")
        if self.colors:
            parts.append(f"Dominant colors: {', '.join(self.colors)}.")
        if self.ocr_text:
            parts.append(f"Text in image: {self.ocr_text}")
        return " ".join(parts)


class VisionPipeline:
    """Loads every vision/OCR model once and reuses them across all images,
    whether they came from test_files/ directly or were embedded in a PDF/PPTX."""

    def __init__(self, ocr_engine: OcrEngine, tagger: ObjectTagger, captioner: Captioner):
        self._ocr_engine = ocr_engine
        self._tagger = tagger
        self._captioner = captioner

    def analyze(self, image: Image.Image) -> VisionResult:
        image = image.convert("RGB")
        return VisionResult(
            colors=extract_dominant_colors(image),
            tags=self._tagger.tag(image),
            ocr_text=self._ocr_engine.extract_text(image),
            caption=self._captioner.caption(image),
        )

    def analyze_bytes(self, image_bytes: bytes) -> VisionResult | None:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
        except Exception:
            return None
        return self.analyze(image)
