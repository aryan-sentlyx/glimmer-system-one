"""Throughput of the single-question defect decision: full depth against early exit at layer 13.

The early exit uses a forward hook on decoder layer 13 that stores its output and stops the forward.
Also checks that the hook output equals hidden_states[13] from a normal forward (same features the head saw).
Usage: cd src && GPU_TYPE=H100 uv run modal run throughput2.py
"""
import os
import modal
from glimmer_image import DATA_MOUNT, MODEL_PATH, WEIGHTS_MOUNT, data_vol, gpu_image, secrets, weights_vol
from prompts import TEMPLATES, SYSTEM_INSPECT

GPU_TYPE = os.environ.get("GPU_TYPE", "H100")
app = modal.App("glimmer-throughput2")


class StopForward(Exception):
    pass


@app.function(image=gpu_image, gpu=GPU_TYPE, volumes={WEIGHTS_MOUNT: weights_vol, DATA_MOUNT: data_vol},
              secrets=secrets, timeout=1800)
def run(max_side: int = 448) -> str:
    import time, torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    from mvtec_data import load_rows
    processor = AutoProcessor.from_pretrained(MODEL_PATH); processor.tokenizer.padding_side = "left"
    model = AutoModelForImageTextToText.from_pretrained(MODEL_PATH, dtype=torch.bfloat16, device_map="cuda").eval()
    lm = model.model.language_model
    rows = load_rows("bottle", "test", limit=32, seed=0)
    imgs = []
    for r in rows:
        im = r.image.copy(); im.thumbnail((max_side, max_side)); imgs.append(im)
    q = TEMPLATES["inspect_defective_v1"][1].format(name="bottle")
    m = [{"role": "system", "content": SYSTEM_INSPECT}, {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": q}]}]
    text = processor.apply_chat_template(m, add_generation_prompt=True, tokenize=False) + " to=user<|message|>"
    lines = [f"GPU {torch.cuda.get_device_name()} | 1 prompt per image | image side {max_side} | {len(lm.layers)} layers"]

    # check: hook output of layer index 12 (the 13th layer) == hidden_states[13]
    store = {}
    def hook(mod, inp, out):
        store["h"] = (out[0] if isinstance(out, tuple) else out)[:, -1].float()
        if store.get("stop"):
            raise StopForward()
    handle = lm.layers[12].register_forward_hook(hook)
    inputs = processor(text=[text], images=[imgs[0]], return_tensors="pt", padding=True); inputs = {k: v.to("cuda") for k, v in inputs.items()}
    with torch.no_grad():
        out = model(**inputs, output_hidden_states=True, use_cache=False, logits_to_keep=1)
    diff = (out.hidden_states[13][:, -1].float() - store["h"]).abs().max().item()
    lines.append(f"check: |hidden_states[13] - hook(layer 13)| max = {diff:.2e}")

    for mode in ("full", "exit13"):
        store["stop"] = (mode == "exit13")
        for B in (1, 4, 8, 16, 32):
            inputs = processor(text=[text] * B, images=imgs[:B], return_tensors="pt", padding=True)
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
            def fwd():
                try:
                    model(**inputs, use_cache=False, logits_to_keep=1)
                except StopForward:
                    pass
            try:
                with torch.no_grad():
                    fwd(); torch.cuda.synchronize(); t0 = time.time(); n = 3
                    for _ in range(n):
                        fwd()
                    torch.cuda.synchronize(); dt = (time.time() - t0) / n
            except torch.OutOfMemoryError:
                lines.append(f"{mode:6s} batch {B:2d}: out of memory"); torch.cuda.empty_cache(); continue
            lines.append(f"{mode:6s} batch {B:2d} | {inputs['input_ids'].shape[1]} tok | {dt*1000:7.1f} ms | {B/dt:6.2f} images/s | {1000*dt/B:6.1f} ms/image")
    handle.remove()
    return "\n".join(lines)


@app.local_entrypoint()
def main():
    print(run.remote())
