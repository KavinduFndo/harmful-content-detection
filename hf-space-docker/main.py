"""
Hugging Face Docker Space API for harmful content detection.

Contract (used by harmful-content-detector backend):
  POST /api/predict
  Body: { "text": str, "lang": str, "categories": list[str] }
  Response: { "scores": { "category_name": float, ... } }
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

# Small zero-shot NLI model; runs on CPU, ~140M params
ZERO_SHOT_MODEL = "MoritzLaurer/DeBERTa-v3-small-mnli"

_classifier = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        from transformers import pipeline
        _classifier = pipeline(
            "zero-shot-classification",
            model=ZERO_SHOT_MODEL,
            device=-1,  # CPU
        )
    return _classifier


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load model at startup so first request is fast
    _get_classifier()
    yield
    # optional: cleanup
    pass


app = FastAPI(title="Harmful Content Classifier", version="1.0", lifespan=lifespan)


class PredictRequest(BaseModel):
    text: str
    lang: str
    categories: list[str]


# Human-readable labels for the zero-shot model (it works better with short phrases)
CATEGORY_LABELS = {
    "harassment_hate_speech": "harassment or hate speech",
    "killings_murder_violent_acts": "killings, murder or violent acts",
    "elder_abuse": "elder abuse",
    "child_abuse": "child abuse",
    "general_violence": "general violence",
}


def _predict(text: str, lang: str, categories: list[str]) -> dict[str, float]:
    if not text.strip():
        return {c: 0.0 for c in categories}

    # Map requested categories to labels the model can score
    labels = [CATEGORY_LABELS.get(c, c.replace("_", " ")) for c in categories]
    classifier = _get_classifier()

    out = classifier(
        text.strip(),
        labels,
        hypothesis_template="This text is about {}.",
        multi_label=True,
    )

    # out["labels"] and out["scores"] are in same order
    score_by_label = dict(zip(out["labels"], out["scores"]))
    # Map back to original category keys
    return {
        cat: float(score_by_label.get(CATEGORY_LABELS.get(cat, cat.replace("_", " ")), 0.0))
        for cat in categories
    }


@app.post("/api/predict")
def predict(req: PredictRequest) -> dict:
    scores = _predict(req.text, req.lang, req.categories)
    return {"scores": scores}


@app.get("/")
def root() -> dict:
    return {"message": "Harmful Content Classifier API", "predict": "POST /api/predict"}
