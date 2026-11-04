"""Thin client for the Meta Model API (Muse Spark). Reads MODEL_API_KEY from .env."""
import base64
import io
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MODEL = os.environ.get("MUSE_MODEL", "muse-spark-1.3")


def client() -> OpenAI:
    key = os.environ.get("MODEL_API_KEY")
    if not key:
        raise RuntimeError("MODEL_API_KEY is not set. Copy .env.example to .env.")
    return OpenAI(api_key=key, base_url=BASE_URL)


def image_to_data_url(img, fmt: str = "JPEG", max_side: int = 768) -> str:
    """Resize a PIL image and encode it as a data URL."""
    img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)))
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/{fmt.lower()};base64,{b64}"


def ask(prompt: str, image=None, model: str = DEFAULT_MODEL, json_mode: bool = False, **kw):
    """Send one prompt with an optional PIL image. Return (text, usage, seconds)."""
    content = [{"type": "text", "text": prompt}]
    if image is not None:
        content.insert(0, {"type": "image_url", "image_url": {"url": image_to_data_url(image)}})
    args = dict(model=model, messages=[{"role": "user", "content": content}], **kw)
    if json_mode:
        args["response_format"] = {"type": "json_object"}
    t0 = time.time()
    r = client().chat.completions.create(**args)
    dt = time.time() - t0
    return r.choices[0].message.content, r.usage, dt


if __name__ == "__main__":
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (256, 256), "white")
    d = ImageDraw.Draw(img)
    d.ellipse((60, 60, 200, 200), fill="silver", outline="black")
    d.line((80, 130, 180, 140), fill="red", width=4)
    text, usage, dt = ask(
        "Look at this part. Reply with JSON: {\"defect_present\": true|false, "
        "\"p_defect\": number 0-1, \"defect_type\": one of [\"scratch\",\"crack\",\"none\"]}",
        image=img, json_mode=True,
    )
    print("response:", text)
    print("usage:", usage)
    print(f"latency: {dt:.2f}s")
