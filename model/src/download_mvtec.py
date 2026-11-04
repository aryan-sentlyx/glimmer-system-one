"""Download the MVTec AD parquet mirror into the glimmer-data volume. Run once.

Usage: uv run modal run src/download_mvtec.py
License of the data: CC BY-NC-SA 4.0 (research use only).
"""
import modal

app = modal.App("mvtec-download")
vol = modal.Volume.from_name("glimmer-data", create_if_missing=True)
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "huggingface_hub[hf_transfer]>=0.34"
).env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})

DATASET_ID = "TheoM55/mvtec_all_objects_split"
MOUNT = "/data"


@app.function(image=image, volumes={MOUNT: vol},
              secrets=[modal.Secret.from_name("glimmer-secrets")], timeout=3600, cpu=4)
def download() -> str:
    import os
    from huggingface_hub import snapshot_download

    target = f"{MOUNT}/mvtec_ad"
    snapshot_download(DATASET_ID, repo_type="dataset", local_dir=target,
                      token=os.environ.get("HF_TOKEN"))
    vol.commit()
    files = sorted(os.listdir(f"{target}/data"))
    total = sum(os.path.getsize(f"{target}/data/{f}") for f in files) / 1e9
    return f"{len(files)} parquet files, {total:.2f} GB at {target}"


@app.local_entrypoint()
def main():
    print(download.remote())
