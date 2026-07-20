from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    """Raw content pulled from a document file.

    Embedded image bytes are handed back raw (not yet analyzed) so vision/
    processing stays in one place regardless of whether an image came from
    test_files/ directly or was embedded in a PDF/PPTX.
    """

    text: str
    embedded_images: list[bytes] = field(default_factory=list)
    structural_metadata: dict = field(default_factory=dict)
