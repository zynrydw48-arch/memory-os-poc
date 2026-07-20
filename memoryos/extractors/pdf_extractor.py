import fitz  # PyMuPDF
from PIL import Image

from memoryos.extractors.result import ExtractionResult
from memoryos.ocr.engine import OcrEngine

MIN_TEXT_CHARS_PER_PAGE = 20  # below this, treat the page as scanned/image-only
MAX_EMBEDDED_IMAGES = 5  # bounds processing time on image-heavy PDFs
SCAN_RENDER_DPI = 150


def extract_pdf(path, ocr_engine: OcrEngine) -> ExtractionResult:
    doc = fitz.open(path)
    text_parts = []
    embedded_images: list[bytes] = []
    ocr_page_count = 0

    for page in doc:
        page_text = page.get_text("text").strip()

        if len(page_text) < MIN_TEXT_CHARS_PER_PAGE:
            pix = page.get_pixmap(dpi=SCAN_RENDER_DPI)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            ocr_text = ocr_engine.extract_text(image)
            if ocr_text:
                ocr_page_count += 1
                page_text = ocr_text

        if page_text:
            text_parts.append(page_text)

        if len(embedded_images) < MAX_EMBEDDED_IMAGES:
            for img_info in page.get_images(full=True):
                if len(embedded_images) >= MAX_EMBEDDED_IMAGES:
                    break
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                embedded_images.append(base_image["image"])

    page_count = len(doc)
    doc.close()

    return ExtractionResult(
        text="\n".join(text_parts),
        embedded_images=embedded_images,
        structural_metadata={"page_count": page_count, "ocr_page_count": ocr_page_count},
    )
