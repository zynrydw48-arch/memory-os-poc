import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from memoryos.database.db import Database
from memoryos.embeddings.provider import EmbeddingProvider
from memoryos.ocr.engine import OcrEngine
from memoryos.ui.main_window import MainWindow
from memoryos.vision.pipeline import VisionPipeline


def run(
    embedding_provider: EmbeddingProvider,
    ocr_engine: OcrEngine,
    vision_pipeline: VisionPipeline,
    database: Database,
    db_path: Path,
) -> int:
    app = QApplication(sys.argv)
    # Sprint 5: captured before any theme is applied, so "Light" always means
    # Qt's real native default, not a hand-rolled approximation.
    original_palette = app.palette()
    original_style_name = app.style().objectName()
    window = MainWindow(
        embedding_provider,
        ocr_engine,
        vision_pipeline,
        database,
        db_path,
        original_palette,
        original_style_name,
    )
    window.show()
    return app.exec()
