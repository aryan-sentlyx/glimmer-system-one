"""Client for the OpenRouter Decisions API (Jev 1.14 and other decision models).

Reads OPENROUTER_API_KEY from .env. Endpoint: POST https://openrouter.ai/api/alpha/decisions
Images go into `state` as base64 data URLs. Jev needs 256 to 1568 px per side, PNG or JPEG.
"""
import base64
import io
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

URL = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_MODEL = os.environ.get("DECISION_MODEL", "typesafe/jev-1.14")


def _key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Add it to .env.")
    return key


def image_part(img, max_side: int = 1024, min_side: int = 280) -> dict:
    """Return an image_url part. Jev rejects images outside 256 to 1568 px per side."""
    img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, max_side / max(w, h))
    if min(w, h) * scale < min_side:
        scale = min_side / min(w, h)
    if scale != 1.0:
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}


def decide(state, questions: dict, model: str = DEFAULT_MODEL, timeout: int = 60):
    """Send one decisions request. Return (answers, usage, seconds, raw)."""
    body = {"model": model, "state": state, "questions": questions}
    t0 = time.time()
    r = requests.post(URL, json=body, timeout=timeout,
                      headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"})
    dt = time.time() - t0
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:500]}")
    data = r.json()
    return data["answers"], data.get("usage", {}), dt, data


# Standard inspection questions, shared with the Glimmer model so the comparison is fair.
def inspection_questions(obj: str, defect_types: list[str]) -> dict:
    return {
        "defective": {"type": "noul",
                      "instructions": f"The {obj} in the photo has a visible manufacturing defect."},
        "defect_type": {"type": "choice",
                        "instructions": f"Which defect does the {obj} in the photo show?",
                        "criteria": {d: None for d in ["good"] + defect_types}},
        "severity": {"type": "score",
                     "instructions": f"How severe is the damage to the {obj}?",
                     "criteria": ["none", "minor", "moderate", "severe"]},
    }


if __name__ == "__main__":
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (512, 512), "white")
    d = ImageDraw.Draw(img)
    d.ellipse((120, 120, 400, 400), fill="silver", outline="black", width=3)
    d.line((160, 260, 360, 280), fill="red", width=8)
    state = ["Photo of a metal part from a production line.", image_part(img)]
    qs = inspection_questions("part", ["scratch", "crack", "dent"])
    answers, usage, dt, raw = decide(state, qs)
    print("model:", raw.get("model"), "| provider:", raw.get("provider"))
    for k, v in answers.items():
        print(f"  {k}: {v}")
    print("usage:", usage)
    print(f"latency: {dt:.2f}s")
