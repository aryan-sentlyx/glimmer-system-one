"""Zero-shot System One decisions with Muse Glimmer: noul, choice, score from one batched forward.

The choice question is order-invariant: every option is scored in its own prompt as a yes/no
question, then the yes-probabilities are normalized. Hidden features at several layers are
saved for the trained head.

Usage:
  cd src && uv run modal run glimmer_decide.py --objects bottle --limit 12
  cd src && uv run modal run glimmer_decide.py --objects all
"""
import os
import modal
from glimmer_image import DATA_MOUNT, MODEL_PATH, WEIGHTS_MOUNT, data_vol, gpu_image, secrets, weights_vol
from prompts import TEMPLATES, SYSTEM_INSPECT

GPU_TYPE = os.environ.get("GPU_TYPE", "H100")
app = modal.App("glimmer-decide")

ALL_OBJECTS = ["bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather", "metal_nut",
               "pill", "screw", "tile", "toothbrush", "transistor", "wood", "zipper"]
FEATURE_LAYERS = (13, 25, 37, 52)
SYSTEM = SYSTEM_INSPECT


@app.cls(image=gpu_image, gpu=GPU_TYPE, volumes={WEIGHTS_MOUNT: weights_vol, DATA_MOUNT: data_vol},
         secrets=secrets, timeout=3600, scaledown_window=120, max_containers=3)
class Glimmer:
    @modal.enter()
    def load(self):
        import torch
        from transformers import AutoProcessor, AutoModelForImageTextToText
        self.torch = torch
        self.processor = AutoProcessor.from_pretrained(MODEL_PATH)
        self.model = AutoModelForImageTextToText.from_pretrained(MODEL_PATH, dtype=torch.bfloat16, device_map="cuda").eval()
        tok = self.processor.tokenizer
        self.yes_ids = sorted({tok.encode(w, add_special_tokens=False)[0] for w in ["yes", " yes", "Yes", " Yes"]})
        self.no_ids = sorted({tok.encode(w, add_special_tokens=False)[0] for w in ["no", " no", "No", " No"]})
        self.digit_ids = [tok.encode(str(d), add_special_tokens=False)[0] for d in range(10)]
        self.processor.tokenizer.padding_side = "left"

    def _prompt(self, question: str) -> str:
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": question}]}]
        text = self.processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        return text + " to=user<|message|>"

    def _forward(self, image, questions: list[str], want_hidden: bool):
        torch = self.torch
        texts = [self._prompt(q) for q in questions]
        inputs = self.processor(text=texts, images=[image] * len(texts), return_tensors="pt", padding=True)
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
        with torch.no_grad():
            torch.cuda.synchronize(); t0 = __import__("time").time()
            out = self.model(**inputs, output_hidden_states=want_hidden)
            torch.cuda.synchronize(); dt = __import__("time").time() - t0
        logp = torch.log_softmax(out.logits[:, -1].float(), dim=-1)  # left padding: last position is real
        feats = None
        if want_hidden:
            feats = torch.stack([out.hidden_states[L][0, -1].float() for L in FEATURE_LAYERS]).half().cpu().numpy()
        return logp, dt, feats, inputs["input_ids"].shape

    def _p_yes(self, logp_row):
        torch = self.torch
        ly = torch.logsumexp(logp_row[self.yes_ids], 0); ln = torch.logsumexp(logp_row[self.no_ids], 0)
        return torch.softmax(torch.stack([ly, ln]), 0)[0].item(), (ly.exp() + ln.exp()).item()

    @modal.method()
    def decide(self, image_bytes: bytes, obj: str, defect_types: list[str], max_side: int = 448,
               want_hidden: bool = True) -> dict:
        import io, time
        from PIL import Image
        torch = self.torch
        t_all = time.time()
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB"); img.thumbnail((max_side, max_side))
        name = obj.replace("_", " ")
        options = ["good"] + defect_types
        qs = [TEMPLATES["inspect_defective_v1"][1].format(name=name)]
        qs += [TEMPLATES["inspect_good_v1"][1].format(name=name) if o == "good"
               else TEMPLATES["inspect_type_v1"][1].format(name=name, opt=o.replace("_", " ")) for o in options]
        qs += [TEMPLATES["inspect_severity_v1"][1].format(name=name)]
        logp, dt, feats, shape = self._forward(img, qs, want_hidden)
        p_def, mass0 = self._p_yes(logp[0])
        opt_p = [self._p_yes(logp[1 + i])[0] for i in range(len(options))]
        z = torch.tensor(opt_p).clamp(1e-6, 1 - 1e-6); z = torch.log(z / (1 - z))
        choice_probs = torch.softmax(z, 0).tolist()
        sev = torch.softmax(logp[-1][self.digit_ids[:4]], 0).tolist()
        severity = float(sum(i * p for i, p in enumerate(sev)))
        best = max(range(len(options)), key=lambda i: choice_probs[i])
        return {"p_defective": p_def, "yes_no_mass": mass0,
                "choice": options[best], "choice_probs": dict(zip(options, choice_probs)),
                "choice_conf": max(choice_probs), "severity": severity, "severity_probs": {str(i): p for i, p in enumerate(sev)},
                "forward_s": dt, "latency_s": time.time() - t_all, "batch": list(shape), "features": feats}

    @modal.method()
    def run_object(self, obj: str, split: str, limit: int | None, seed: int, max_side: int) -> dict:
        import io, numpy as np
        from mvtec_data import load_rows
        rows_all = load_rows(obj, "test", limit=None, seed=seed)
        defect_types = sorted({r.defect for r in rows_all if r.defect != "good"})
        rows = rows_all if split == "test" else load_rows(obj, split, limit=None, seed=seed)
        if limit:
            rows = rows[:limit]
        recs, feats = [], []
        for i, r in enumerate(rows):
            buf = io.BytesIO(); r.image.save(buf, format="PNG")
            d = self.decide.local(buf.getvalue(), obj, defect_types, max_side=max_side)
            feats.append(d.pop("features"))
            d.update({"model": f"glimmer-30b-zeroshot-{max_side}", "object": obj, "split": split, "idx": i,
                      "label": r.label, "defect": r.defect, "defect_types": defect_types})
            recs.append(d)
        os.makedirs(f"{DATA_MOUNT}/features", exist_ok=True)
        np.save(f"{DATA_MOUNT}/features/{obj}.{split}.{max_side}.npy", np.stack(feats))
        data_vol.commit()
        return {"obj": obj, "recs": recs}


@app.local_entrypoint()
def main(objects: str = "bottle", limit: int = 0, seed: int = 0, max_side: int = 448, split: str = "test"):
    import json
    from bench_decisions import summarize
    objs = ALL_OBJECTS if objects == "all" else objects.split(",")
    g = Glimmer()
    results = []
    for part in g.run_object.starmap([(o, split, limit or None, seed, max_side) for o in objs]):
        results.extend(part["recs"])
        s = summarize(part["recs"])
        print(f"  {part['obj']:12s} n={s.get('n')} auroc={s.get('noul_auroc')} acc={s.get('noul_acc@0.5')} "
              f"choice_acc={s.get('choice_acc')} fwd_p50={__import__('numpy').median([r['forward_s'] for r in part['recs']]):.3f}s", flush=True)
    os.makedirs("../../results/decisions", exist_ok=True)
    tag = "" if objects == "all" else "_" + objects.replace(",", "+")
    fname = f"../../results/decisions/glimmer-30b-zeroshot-{max_side}{tag}.{split}.jsonl"
    with open(fname, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(results)} rows to {fname}")
    print(json.dumps(summarize(results), indent=2))
