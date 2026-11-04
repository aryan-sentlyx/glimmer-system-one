"""Throughput of the Glimmer decision model on one GPU: images per second at several batch sizes.

Each image needs 6 prompts (1 noul + 4 choice options + 1 score). A batch of B images is 6*B sequences.
Usage: cd src && GPU_TYPE=H100 uv run modal run throughput.py
"""
import os
import modal
from glimmer_image import DATA_MOUNT, MODEL_PATH, WEIGHTS_MOUNT, data_vol, gpu_image, secrets, weights_vol
from prompts import TEMPLATES, SYSTEM_INSPECT

GPU_TYPE = os.environ.get("GPU_TYPE", "H100")
app = modal.App("glimmer-throughput")


@app.function(image=gpu_image, gpu=GPU_TYPE, volumes={WEIGHTS_MOUNT: weights_vol, DATA_MOUNT: data_vol},
              secrets=secrets, timeout=1800)
def run(max_side: int = 448) -> str:
    import time, torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    from mvtec_data import load_rows
    processor = AutoProcessor.from_pretrained(MODEL_PATH); processor.tokenizer.padding_side = "left"
    model = AutoModelForImageTextToText.from_pretrained(MODEL_PATH, dtype=torch.bfloat16, device_map="cuda").eval()
    rows = load_rows("bottle", "test", limit=32, seed=0)
    imgs = []
    for r in rows:
        im = r.image.copy(); im.thumbnail((max_side, max_side)); imgs.append(im)
    name = "bottle"; opts = ["good", "broken large", "broken small", "contamination"]
    qs = [TEMPLATES["inspect_defective_v1"][1].format(name=name)]
    qs += [TEMPLATES["inspect_good_v1"][1].format(name=name)] + [TEMPLATES["inspect_type_v1"][1].format(name=name, opt=o) for o in opts[1:]]
    qs += [TEMPLATES["inspect_severity_v1"][1].format(name=name)]

    def prompt(q):
        m = [{"role": "system", "content": SYSTEM_INSPECT}, {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": q}]}]
        return processor.apply_chat_template(m, add_generation_prompt=True, tokenize=False) + " to=user<|message|>"
    texts = [prompt(q) for q in qs]
    lines = [f"GPU {torch.cuda.get_device_name()} | {len(qs)} prompts per image | image side {max_side}"]
    for B in (1, 2, 4, 8, 16):
        batch_imgs = [im for im in imgs[:B] for _ in qs]; batch_txt = texts * B
        inputs = processor(text=batch_txt, images=batch_imgs, return_tensors="pt", padding=True)
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
        kw = dict(use_cache=False, logits_to_keep=1)  # last-position logits only: saves memory
        try:
            with torch.no_grad():
                model(**inputs, **kw); torch.cuda.synchronize()  # warm-up
                t0 = time.time(); n = 3
                for _ in range(n):
                    out = model(**inputs, **kw); _ = out.logits[:, -1].float()
                torch.cuda.synchronize(); dt = (time.time() - t0) / n
        except torch.OutOfMemoryError:
            lines.append(f"batch {B:2d} images: out of memory"); torch.cuda.empty_cache(); continue
        seq = inputs["input_ids"].shape
        lines.append(f"batch {B:2d} images = {seq[0]:3d} seqs x {seq[1]} tok | {dt*1000:7.1f} ms | {B/dt:6.2f} images/s | "
                     f"{1000*dt/B:6.1f} ms/image | peak mem {torch.cuda.max_memory_allocated()/1e9:.1f} GB")
    return "\n".join(lines)


@app.local_entrypoint()
def main():
    print(run.remote())
