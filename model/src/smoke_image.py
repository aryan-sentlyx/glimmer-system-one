"""Build the GPU image and check that the Muse Glimmer model class exists. CPU only.

Usage: uv run modal run src/smoke_image.py
"""
import modal
from glimmer_image import gpu_image

app = modal.App("glimmer-smoke-image")


@app.function(image=gpu_image, timeout=600)
def check() -> str:
    import torch
    import transformers

    has_cls = hasattr(transformers, "MuseGlimmerForConditionalGeneration")
    return f"transformers {transformers.__version__}, torch {torch.__version__}, MuseGlimmer class: {has_cls}"


@app.local_entrypoint()
def main():
    print(check.remote())
