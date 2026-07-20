from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor

DEFAULT_MODEL_NAME = "Salesforce/blip-image-captioning-base"
MAX_NEW_TOKENS = 30


class Captioner:
    """Sentence-level scene description (BLIP-base). Heavier than ObjectTagger,
    but gives the natural-language "scene description" the spec asks for."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self._processor = BlipProcessor.from_pretrained(model_name)
        self._model = BlipForConditionalGeneration.from_pretrained(model_name)

    def caption(self, image: Image.Image) -> str:
        inputs = self._processor(image.convert("RGB"), return_tensors="pt")
        output_ids = self._model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS)
        return self._processor.decode(output_ids[0], skip_special_tokens=True).strip()
