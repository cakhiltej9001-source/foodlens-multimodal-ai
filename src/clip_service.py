"""Optional local CLIP zero-shot label scoring.

This module is intentionally not imported by the main app so the default installation
remains lightweight. Install requirements-clip.txt, then integrate `rank_food_labels`
into the UI to demonstrate local vision embeddings alongside Gemini reasoning.
"""
from __future__ import annotations

from PIL import Image

DEFAULT_LABELS = [
    "biryani", "plain rice", "fried rice", "idli", "dosa", "upma", "poha",
    "chapati", "naan", "dal", "sambar", "rasam", "paneer curry", "chicken curry",
    "fish curry", "vegetable curry", "salad", "soup", "pizza", "burger", "pasta",
    "noodles", "sandwich", "omelette", "boiled egg", "fruit bowl", "cake", "ice cream",
]


def rank_food_labels(image: Image.Image, labels: list[str] | None = None, top_k: int = 5):
    import torch
    from transformers import CLIPModel, CLIPProcessor

    labels = labels or DEFAULT_LABELS
    model_name = "openai/clip-vit-base-patch32"
    model = CLIPModel.from_pretrained(model_name)
    processor = CLIPProcessor.from_pretrained(model_name)
    prompts = [f"a photo of {label}" for label in labels]
    inputs = processor(text=prompts, images=image, return_tensors="pt", padding=True)
    with torch.inference_mode():
        outputs = model(**inputs)
        probabilities = outputs.logits_per_image.softmax(dim=1)[0]
    top_values, top_indices = torch.topk(probabilities, k=min(top_k, len(labels)))
    return [
        {"label": labels[index], "score": float(value)}
        for value, index in zip(top_values.tolist(), top_indices.tolist())
    ]
