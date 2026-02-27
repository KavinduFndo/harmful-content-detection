Place your trained Sinhala+English NLP model directory or weights here.

Supported runtime adapters are implemented in the API:
- HuggingFace pipeline (if model folder is available)
- PyTorch `.pt` file loading
- Optional custom adapter in `infer.py` (`predict(text, lang, categories)`)
- Optional `label_map.json` for index->category mapping
- Fallback heuristic demo classifier
