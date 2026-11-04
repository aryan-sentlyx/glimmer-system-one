"""Download the Muse Glimmer weights into a Modal volume. Run once.

Usage: uv run modal run src/download_weights.py
"""
import modal

app = modal.App("glimmer-download")
vol = modal.Volume.from_name("glimmer-weights", create_if_missing=True)
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "huggingface_hub[hf_transfer]>=0.34"
).env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})

MODEL_ID = "meta-models/Muse-Glimmer-30B"
MOUNT = "/weights"


@app.function(
    image=image,
    volumes={MOUNT: vol},
    secrets=[modal.Secret.from_name("glimmer-secrets")],
    timeout=60 * 60,
    cpu=4,
)
def download() -> str:
    import os
    from huggingface_hub import snapshot_download

    target = f"{MOUNT}/{MODEL_ID}"
    path = snapshot_download(
        MODEL_ID,
        local_dir=target,
        token=os.environ.get("HF_TOKEN"),
    )
    vol.commit()
    total = 0
    for root, _, files in os.walk(target):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    return f"downloaded to {path}, {total / 1e9:.1f} GB"


@app.local_entrypoint()
def main():
    print(download.remote())
