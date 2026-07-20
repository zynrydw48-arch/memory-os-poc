"""Desktop entrypoint. Run with: python -m memoryos.app_main"""

import os
import sys

from memoryos.utils import app_paths
from memoryos.utils.crash_logging import install_crash_logging

# Sprint 9: a windowed (console=False) frozen build has no console, so this
# must run before anything else -- including the HF/torch setup below, whose
# print() call would otherwise crash the app if sys.stdout is None.
install_crash_logging()

# Sprint 6: when frozen, point HF/torch's cache lookup at the bundled offline
# model cache -- and forbid any network fallback -- before anything that
# might import torch/transformers/sentence_transformers runs below, since
# those libraries read these env vars once at import/first-use time.
if app_paths.is_frozen():
    _model_cache_dir = app_paths.get_resource_dir() / "model_cache"
    os.environ["HF_HOME"] = str(_model_cache_dir)
    os.environ["TORCH_HOME"] = str(_model_cache_dir)
    os.environ["HF_HUB_OFFLINE"] = "1"  # fail loudly locally rather than ever reaching the network

from memoryos.database.db import Database
from memoryos.embeddings.sentence_transformer_provider import SentenceTransformerProvider
from memoryos.ocr.tesseract_engine import TesseractOcrEngine
from memoryos.ui.app import run
from memoryos.vision.caption import Captioner
from memoryos.vision.pipeline import VisionPipeline
from memoryos.vision.tags import ObjectTagger

DB_PATH = app_paths.get_user_data_dir() / "memoryos.sqlite3"


def main() -> None:
    print("Loading models (embedding, OCR, vision)...")
    embedding_provider = SentenceTransformerProvider()
    ocr_engine = TesseractOcrEngine()
    vision_pipeline = VisionPipeline(ocr_engine, ObjectTagger(), Captioner())
    database = Database(DB_PATH)

    exit_code = run(embedding_provider, ocr_engine, vision_pipeline, database, DB_PATH)
    database.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
