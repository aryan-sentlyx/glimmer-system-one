"""Probe Muse Glimmer on one H100: prompt format, zero-shot option scoring, latency.

Usage: cd src && uv run modal run glimmer_probe.py
"""
import modal
from glimmer_image import DATA_MOUNT, MODEL_PATH, WEIGHTS_MOUNT, data_vol, gpu_image, secrets, weights_vol

import os
GPU_TYPE = os.environ.get("GPU_TYPE", "H100")
app = modal.App("glimmer-probe")


@app.function(image=gpu_image, gpu=GPU_TYPE, volumes={WEIGHTS_MOUNT: weights_vol, DATA_MOUNT: data_vol},
              secrets=secrets, timeout=1800)
def probe() -> str:
    import time, json
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
    from mvtec_data import load_rows

    out = []
    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL_PATH)
    model = AutoModelForImageTextToText.from_pretrained(MODEL_PATH, dtype=torch.bfloat16, device_map="cuda")
    model.eval()
    out.append(f"load: {time.time()-t0:.1f}s, gpu mem {torch.cuda.memory_allocated()/1e9:.1f} GB")
    out.append(f"model class: {type(model).__name__}; lm layers: {model.config.text_config.num_hidden_layers if hasattr(model.config,'text_config') else '?'}")

    rows = load_rows("bottle", "test", limit=2, seed=1)
    row = next(r for r in rows if r.label == 1) if any(r.label == 1 for r in rows) else rows[0]
    out.append(f"sample: obj={row.obj} defect={row.defect} label={row.label} size={row.image.size}")

    def build(image, question: str, max_side: int):
        img = image.copy()
        img.thumbnail((max_side, max_side))
        messages = [
            {"role": "system", "content": "You are an inspection system. Answer with one word. Reasoning strength: low."},
            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": question}]},
        ]
        text = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        text = text + " to=user<|message|>"
        inputs = processor(text=[text], images=[img], return_tensors="pt")
        return {k: v.to("cuda") for k, v in inputs.items()}, text

    question = "Is this bottle defective? Answer yes or no."
    inputs, text = build(row.image, question, 448)
    out.append("prompt tail: " + repr(text[-200:]))
    out.append(f"input tokens: {inputs['input_ids'].shape[1]}")

    # 1) zero-shot generation to verify the format
    with torch.no_grad():
        t0 = time.time()
        gen = model.generate(**inputs, max_new_tokens=16, do_sample=False)
        dt = time.time() - t0
    decoded = processor.batch_decode(gen[:, inputs["input_ids"].shape[1]:], skip_special_tokens=False)[0]
    out.append(f"generate (16 tok): {dt:.2f}s -> {decoded!r}")

    # 2) option scoring from the last-token logits: P(yes) vs P(no)
    tok = processor.tokenizer
    yes_ids = [tok.encode(w, add_special_tokens=False)[0] for w in ["yes", " yes", "Yes", " Yes"]]
    no_ids = [tok.encode(w, add_special_tokens=False)[0] for w in ["no", " no", "No", " No"]]
    out.append(f"yes ids {yes_ids} no ids {no_ids}")

    def score(inputs, layers=(13, 25, 37, 52)):
        with torch.no_grad():
            torch.cuda.synchronize(); t0 = time.time()
            res = model(**inputs, output_hidden_states=True)
            torch.cuda.synchronize(); dt = time.time() - t0
        logits = res.logits[0, -1].float()
        lp = torch.log_softmax(logits, -1)
        p_yes = torch.logsumexp(lp[yes_ids], 0).exp().item()
        p_no = torch.logsumexp(lp[no_ids], 0).exp().item()
        hs = res.hidden_states
        pooled = {L: hs[L][0, -1].float().norm().item() for L in layers if L < len(hs)}
        return dt, p_yes, p_no, len(hs), pooled

    for side in (224, 448, 896):
        inputs, _ = build(row.image, question, side)
        dt, p_yes, p_no, n_hs, pooled = score(inputs)
        out.append(f"side={side} tokens={inputs['input_ids'].shape[1]} forward={dt*1000:.0f}ms "
                   f"p_yes={p_yes:.3f} p_no={p_no:.3f} norm_yes={p_yes/(p_yes+p_no+1e-9):.3f} hidden_states={n_hs}")

    # 3) a good sample for contrast
    good = next((r for r in load_rows("bottle", "test", limit=20, seed=2) if r.label == 0), None)
    if good:
        inputs, _ = build(good.image, question, 448)
        dt, p_yes, p_no, _, _ = score(inputs)
        out.append(f"GOOD sample side=448 forward={dt*1000:.0f}ms p_yes={p_yes:.3f} p_no={p_no:.3f} norm_yes={p_yes/(p_yes+p_no+1e-9):.3f}")

    # 4) early-exit timing: run only the first N layers of the language model
    try:
        lm = model.model.language_model if hasattr(model.model, "language_model") else None
        out.append(f"language_model attr: {type(lm).__name__ if lm else None}; layers attr: {hasattr(lm, 'layers') if lm else None}")
    except Exception as e:
        out.append(f"early-exit introspection failed: {e}")

    return "\n".join(out)


@app.local_entrypoint()
def main():
    print(probe.remote())
