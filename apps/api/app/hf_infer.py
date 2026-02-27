"""
Custom NLP adapter that calls a Hugging Face-hosted model endpoint.

Required environment variables:
- HF_MODEL_URL: Full endpoint URL (e.g. Space API endpoint or Inference Endpoint)
Optional:
- HF_API_TOKEN: HF access token for private endpoints
- HF_TIMEOUT_SEC: Request timeout in seconds (default: 30)
"""

from __future__ import annotations

import os
from typing import Any

import requests


def _default_scores(categories: list[str]) -> dict[str, float]:
    return {category: 0.0 for category in categories}


def _normalize_label(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _match_category(label: str, categories: list[str]) -> str | None:
    normalized_label = _normalize_label(label)
    for category in categories:
        normalized_category = _normalize_label(category)
        if normalized_label == normalized_category:
            return category
        if normalized_label in normalized_category or normalized_category in normalized_label:
            return category
    return None


def _extract_scores(payload: Any, categories: list[str]) -> dict[str, float]:
    scores = _default_scores(categories)

    if isinstance(payload, dict):
        for key, value in payload.items():
            category = _match_category(str(key), categories)
            if category is None:
                continue
            try:
                scores[category] = max(scores[category], float(value))
            except Exception:
                continue
        return scores

    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            label = item.get("label")
            score = item.get("score")
            if label is None or score is None:
                continue
            category = _match_category(str(label), categories)
            if category is None:
                continue
            try:
                scores[category] = max(scores[category], float(score))
            except Exception:
                continue
        return scores

    return scores


def predict(text: str, lang: str, categories: list[str]) -> dict[str, float]:
    model_url = os.getenv("HF_MODEL_URL", "").strip()
    if not model_url:
        return _default_scores(categories)

    timeout_sec = int(os.getenv("HF_TIMEOUT_SEC", "30"))
    api_token = os.getenv("HF_API_TOKEN", "").strip()

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    body = {"text": text, "lang": lang, "categories": categories}

    try:
        response = requests.post(model_url, json=body, headers=headers, timeout=timeout_sec)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return _default_scores(categories)

    if isinstance(data, dict) and "labels" in data and "scores" in data:
        labels = data.get("labels") or []
        values = data.get("scores") or []
        transformed = []
        for idx, label in enumerate(labels):
            if idx >= len(values):
                break
            transformed.append({"label": label, "score": values[idx]})
        return _extract_scores(transformed, categories)

    if isinstance(data, dict) and "scores" in data:
        return _extract_scores(data["scores"], categories)

    return _extract_scores(data, categories)
