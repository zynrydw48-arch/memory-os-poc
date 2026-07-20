import os
from pathlib import Path

import pytesseract
from PIL import Image

from memoryos.ocr.engine import OcrEngine
from memoryos.utils import app_paths

DEFAULT_LANGUAGES = "eng+heb"

# tessdata (contains eng + heb) so this doesn't depend on whatever's bundled
# with the system Tesseract install, which on Windows ships English-only by
# default. Resolves to the project root when running from source (unchanged
# dev behavior) or the PyInstaller-bundled resource dir when frozen (Sprint 6).
DEFAULT_TESSDATA_DIR = app_paths.get_resource_dir() / "tessdata"

# Sprint 6: prefer a bundled Tesseract-OCR copy (frozen app) over the system
# install (dev machine), so a frozen build never depends on winget having
# been run. Falls back to the system path exactly as before if neither the
# bundle nor that fallback path exists (pytesseract's own PATH lookup then
# takes over, unchanged from before this sprint).
_BUNDLED_TESSERACT_EXE = app_paths.get_resource_dir() / "Tesseract-OCR" / "tesseract.exe"
_SYSTEM_TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")

if _BUNDLED_TESSERACT_EXE.exists():
    pytesseract.pytesseract.tesseract_cmd = str(_BUNDLED_TESSERACT_EXE)
elif _SYSTEM_TESSERACT_EXE.exists():
    pytesseract.pytesseract.tesseract_cmd = str(_SYSTEM_TESSERACT_EXE)


class TesseractOcrEngine(OcrEngine):
    def __init__(
        self,
        languages: str = DEFAULT_LANGUAGES,
        tessdata_dir: Path = DEFAULT_TESSDATA_DIR,
    ):
        self._languages = languages
        os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)

    def extract_text(self, image: Image.Image) -> str:
        text = pytesseract.image_to_string(image.convert("RGB"), lang=self._languages)
        return text.strip()
