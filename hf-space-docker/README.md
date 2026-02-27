---
title: Harmful Content Classifier API
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# Harmful Content Classifier API

Docker Space that exposes a **POST /api/predict** endpoint for the [harmful-content-detector](https://github.com/your-org/harmful-content-detector) backend.

## API contract

- **URL:** `POST /api/predict`
- **Body:** `{ "text": string, "lang": string, "categories": string[] }`
- **Response:** `{ "scores": { "category_name": number, ... } }`

## Using this Space from the detector

1. After this Space is built and running, open **Settings → General** and turn on **"Duplicate this Space"** if you want a serverless API.
2. Set in your backend (e.g. DigitalOcean env or `.env`):
   - **HF_MODEL_URL** = `https://YOUR_USERNAME-YOUR_SPACE_NAME.hf.space/api/predict`  
     (e.g. `https://johndoe-harmful-content-classifier.hf.space/api/predict`)
   - **HF_API_TOKEN** = your Hugging Face token (Read) from [Settings → Access Tokens](https://huggingface.co/settings/tokens).

## Adding a different model

Edit `main.py`: change `ZERO_SHOT_MODEL` or replace `_predict()` to use your own model. Keep the same request/response shape. Default is `MoritzLaurer/DeBERTa-v3-small-mnli` (zero-shot NLI, runs on CPU).

## Local run

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 7860
# POST http://localhost:7860/api/predict
```
