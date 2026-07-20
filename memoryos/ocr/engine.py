"""OCR engine interface, kept separate from vision/ so the recognition
backend (EasyOCR today, Tesseract or another engine later) can be swapped
without touching anything that calls it."""

from abc import ABC, abstractmethod

from PIL import Image


class OcrEngine(ABC):
    @abstractmethod
    def extract_text(self, image: Image.Image) -> str:
        """Return recognized text from an image, empty string if none found."""
