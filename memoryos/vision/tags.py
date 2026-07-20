import torch
from PIL import Image
from torchvision import models

DEFAULT_TOP_K = 5
DEFAULT_MIN_CONFIDENCE = 0.15


class ObjectTagger:
    """Lightweight ImageNet tag classifier (MobileNetV2, ~14MB) -- gives discrete
    object/scene tags, distinct from the free-form sentence produced by Captioner."""

    def __init__(
        self, top_k: int = DEFAULT_TOP_K, min_confidence: float = DEFAULT_MIN_CONFIDENCE
    ):
        weights = models.MobileNet_V2_Weights.DEFAULT
        self._model = models.mobilenet_v2(weights=weights)
        self._model.eval()
        self._categories = weights.meta["categories"]
        self._transform = weights.transforms()
        self._top_k = top_k
        self._min_confidence = min_confidence

    def tag(self, image: Image.Image) -> list[str]:
        tensor = self._transform(image.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            logits = self._model(tensor)
            probs = torch.nn.functional.softmax(logits[0], dim=0)

        top_probs, top_indices = torch.topk(probs, self._top_k)
        tags = []
        for prob, index in zip(top_probs.tolist(), top_indices.tolist()):
            if prob >= self._min_confidence:
                tags.append(self._categories[index])
        return tags
