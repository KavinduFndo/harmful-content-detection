import json
from pathlib import Path


SAMPLES = [
    {
        "platform": "demo",
        "platform_post_id": "demo-1",
        "author": "user_a",
        "url": "https://example.com/demo/1",
        "text": "They plan to kill him with a weapon tonight.",
        "media_paths": [],
    },
    {
        "platform": "demo",
        "platform_post_id": "demo-2",
        "author": "user_b",
        "url": "https://example.com/demo/2",
        "text": "මෙම වීඩියෝවේ දැඩි ගැටුමක් සහ අවි පෙන්වයි.",
        "media_paths": [],
    },
    {
        "platform": "demo",
        "platform_post_id": "demo-3",
        "author": "user_c",
        "url": "https://example.com/demo/3",
        "text": "Possible child abuse signs reported by neighbors.",
        "media_paths": [],
    },
]


def main() -> None:
    out_dir = Path("data/demo_inputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, sample in enumerate(SAMPLES, start=1):
        out = out_dir / f"sample_{idx}.json"
        out.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(SAMPLES)} demo samples in {out_dir}")


if __name__ == "__main__":
    main()
