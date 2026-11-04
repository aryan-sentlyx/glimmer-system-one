"""Shared Modal image and volume definitions for Muse Glimmer jobs."""
import modal

MODEL_ID = "meta-models/Muse-Glimmer-30B"
WEIGHTS_MOUNT = "/weights"
DATA_MOUNT = "/data"
MODEL_PATH = f"{WEIGHTS_MOUNT}/{MODEL_ID}"

weights_vol = modal.Volume.from_name("glimmer-weights", create_if_missing=True)
data_vol = modal.Volume.from_name("glimmer-data", create_if_missing=True)
secrets = [modal.Secret.from_name("glimmer-secrets")]

# transformers 5.15.0.dev0 is needed for MuseGlimmerForConditionalGeneration.
gpu_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu24.04", add_python="3.12")
    .apt_install("git")
    .pip_install(
        "torch==2.9.0",
        "accelerate>=1.10",
        "peft>=0.17",
        "bitsandbytes>=0.48",
        "safetensors>=0.6",
        "pillow",
        "pyarrow",
        "pandas",
        "numpy",
        "scikit-learn",
        "fastapi[standard]",
        "huggingface_hub[hf_transfer]>=0.34",
    )
    .pip_install("git+https://github.com/huggingface/transformers.git@main")
    .pip_install("torchvision==0.24.0")  # MuseGlimmerImageProcessor needs the torchvision backend
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/weights/hf_home"})
)

# Mount the sibling modules into every container (runtime mount, no rebuild).
LOCAL_MODULES = ("glimmer_image", "mvtec_data", "decisions_client", "muse_client", "prompts")
gpu_image = gpu_image.add_local_python_source(*LOCAL_MODULES)
