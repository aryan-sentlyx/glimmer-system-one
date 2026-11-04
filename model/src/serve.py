"""Web API for the Glimmer System One model. Same request shape as the Decisions API.

POST /decide  JSON body:
  {"state": "text...", "image": "<base64 jpeg/png>" (optional), "max_side": 448,
   "questions": {
     "defective": {"type": "noul", "instructions": "The part has a visible defect."},
     "type": {"type": "choice", "instructions": "Which defect?", "criteria": {"good": null, "scratch": null}},
     "severity": {"type": "score", "instructions": "How severe?", "criteria": ["none", "minor", "moderate", "severe"]}
   }}
Returns {"answers": {...}, "usage": {...}, "timing": {...}}.
Optional: a trained head in /data/head/<name>.npz is applied when the question has "head": "<name>".
A head needs an image. Without an image the question falls back to zero-shot mode.

The demo backend (demo/backend/app.py) calls the same logic with SystemOne().decide_rpc.remote(body).

Deploy: cd model/src && uv run modal deploy serve.py
"""
import os
import modal
from glimmer_image import DATA_MOUNT, MODEL_PATH, WEIGHTS_MOUNT, data_vol, gpu_image, secrets, weights_vol
from prompts import TEMPLATES, SYSTEM_GENERIC

GPU_TYPE = os.environ.get("GPU_TYPE", "H100")
app = modal.App("glimmer-systemone")
SYSTEM = SYSTEM_GENERIC
FEATURE_LAYERS = (13, 25, 37, 52)
VERSION = "0.4-text"


@app.cls(image=gpu_image, gpu=GPU_TYPE, volumes={WEIGHTS_MOUNT: weights_vol, DATA_MOUNT: data_vol},
         secrets=secrets, timeout=600, scaledown_window=int(os.environ.get("IDLE_S", "600")), max_containers=1)
@modal.concurrent(max_inputs=4)
class SystemOne:
    @modal.enter()
    def load(self):
        import glob, json, numpy as np, torch
        from transformers import AutoProcessor, AutoModelForImageTextToText
        self.torch = torch
        self.processor = AutoProcessor.from_pretrained(MODEL_PATH)
        self.processor.tokenizer.padding_side = "left"
        self.model = AutoModelForImageTextToText.from_pretrained(MODEL_PATH, dtype=torch.bfloat16, device_map="cuda").eval()
        tok = self.processor.tokenizer
        self.yes_ids = sorted({tok.encode(w, add_special_tokens=False)[0] for w in ["yes", " yes", "Yes", " Yes"]})
        self.no_ids = sorted({tok.encode(w, add_special_tokens=False)[0] for w in ["no", " no", "No", " No"]})
        self.digit_ids = [tok.encode(str(d), add_special_tokens=False)[0] for d in range(10)]
        self.heads = {}
        for f in glob.glob(f"{DATA_MOUNT}/head/*.npz"):
            z = np.load(f); self.heads[os.path.basename(f)[:-4]] = {k: z[k] for k in z.files}
        tp = f"{DATA_MOUNT}/head/temp_noul.json"
        self.temp = json.load(open(tp)) if os.path.exists(tp) else None  # zero-shot calibration (T, b)
        # warm-up: one image call and one text call
        from PIL import Image
        self._run(Image.new("RGB", (448, 448), "gray"), "warm-up", ["Is this gray? Answer yes or no."], False)
        self._run(None, "warm-up", ["Is two larger than one? Answer yes or no."], False)

    def _prompt(self, state: str, q: str, system: str = SYSTEM, with_image: bool = True) -> str:
        text = f"{state}\n\n{q}" if state else q
        content = [{"type": "image"}, {"type": "text", "text": text}] if with_image else text
        messages = [{"role": "system", "content": system}, {"role": "user", "content": content}]
        t = self.processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        return t + " to=user<|message|>"

    def _run(self, image, state, questions, want_hidden):
        """One batched forward pass. image is a PIL image or None. Returns (logp, seconds, hidden, tokens)."""
        import time
        torch = self.torch
        has = image is not None
        texts = [self._prompt(state, q, with_image=has) if isinstance(q, str) else self._prompt("", q[1], q[0], has)
                 for q in questions]
        if has:
            inputs = self.processor(text=texts, images=[image] * len(texts), return_tensors="pt", padding=True)
        else:
            inputs = self.processor.tokenizer(texts, return_tensors="pt", padding=True)
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
        with torch.no_grad():
            torch.cuda.synchronize(); t0 = time.time()
            out = self.model(**inputs, output_hidden_states=want_hidden)
            torch.cuda.synchronize(); dt = time.time() - t0
        logp = torch.log_softmax(out.logits[:, -1].float(), dim=-1)
        hidden = {L: out.hidden_states[L][:, -1].float().cpu().numpy() for L in FEATURE_LAYERS} if want_hidden else None
        return logp, dt, hidden, int(inputs["input_ids"].shape[1])

    def _p_yes(self, row):
        torch = self.torch
        ly = torch.logsumexp(row[self.yes_ids], 0); ln = torch.logsumexp(row[self.no_ids], 0)
        return torch.softmax(torch.stack([ly, ln]), 0)[0].item()

    def _apply_head(self, name, hidden, i):
        import numpy as np
        h = self.heads[name]; L = int(h["layer"]); x = (hidden[L][i] - h["mean"]) / h["scale"]
        return float(1 / (1 + np.exp(-(x @ h["coef"] + h["intercept"]))))

    def _decide(self, body: dict) -> dict:
        import base64, io, time
        from PIL import Image
        torch = self.torch
        t_all = time.time()
        img = None
        if body.get("image"):
            img = Image.open(io.BytesIO(base64.b64decode(body["image"]))).convert("RGB")
            side = int(body.get("max_side", 448)); img.thumbnail((side, side))
        state = body.get("state", "") if isinstance(body.get("state"), str) else ""
        if img is None and not state:
            raise ValueError("the request needs an image or a state text")
        if not body.get("questions"):
            raise ValueError("the request needs at least one question")

        def head_ok(q):
            return img is not None and q.get("head") in self.heads and "template" in self.heads[q["head"]]

        qs, plan = [], []
        for name, q in body["questions"].items():
            t = q["type"]; ins = q.get("instructions", "")
            if t == "noul":
                if head_ok(q):
                    sysp, fmt = TEMPLATES[str(self.heads[q["head"]]["template"])]
                    qs.append((sysp, fmt.format(name=body.get("object", "part"))))  # exact training prompt
                else:
                    qs.append(f"{ins} Is this statement true? Answer yes or no.")
                plan.append((name, t, [len(qs) - 1], None))
            elif t == "choice":
                opts = list(q["criteria"]); idx = []
                for o in opts:
                    desc = q["criteria"][o]
                    qs.append(f"{ins} Is the answer '{o}'{(' (' + desc + ')') if desc else ''}? Answer yes or no."); idx.append(len(qs) - 1)
                plan.append((name, t, idx, opts))
            elif t == "score":
                levels = list(q["criteria"]); scale = ", ".join(f"{i} is {l}" for i, l in enumerate(levels))
                qs.append(f"{ins} Rate on a scale from 0 to {len(levels)-1}, where {scale}. Answer with one digit.")
                plan.append((name, t, [len(qs) - 1], levels))
            else:
                raise ValueError(f"unknown question type '{t}' for question '{name}'")
        want_hidden = any(head_ok(q) for q in body["questions"].values())
        logp, dt, hidden, ntok = self._run(img, state, qs, want_hidden)
        answers = {}
        for name, t, idx, extra in plan:
            q = body["questions"][name]
            if t == "noul":
                if head_ok(q):
                    p, mode = self._apply_head(q["head"], hidden, idx[0]), "head:" + q["head"]
                else:
                    p = min(max(self._p_yes(logp[idx[0]]), 1e-6), 1 - 1e-6); mode = "zero-shot"
                    if self.temp and not q.get("raw"):
                        import math
                        p = 1 / (1 + math.exp(-(math.log(p / (1 - p)) / self.temp["T"] + self.temp["b"]))); mode = "zero-shot+temperature"
                answers[name] = {"type": "noul", "noul": round(p, 4), "mode": mode}
            elif t == "choice":
                ps = torch.tensor([self._p_yes(logp[i]) for i in idx]).clamp(1e-6, 1 - 1e-6)
                probs = torch.softmax(torch.log(ps / (1 - ps)), 0).tolist()
                gate = q.get("gate")  # compose: P(good) comes from a noul answer, the rest is split by type
                if gate in answers and answers[gate]["type"] == "noul" and q.get("gate_option", "good") in extra:
                    g = answers[gate]["noul"]; gi = extra.index(q.get("gate_option", "good"))
                    rest = sum(p for i, p in enumerate(probs) if i != gi) or 1.0
                    probs = [(1 - g) if i == gi else g * p / rest for i, p in enumerate(probs)]
                best = max(range(len(extra)), key=lambda i: probs[i])
                answers[name] = {"type": "choice", "choice": extra[best], "confidence": round(max(probs), 4),
                                 "probabilities": {o: round(p, 4) for o, p in zip(extra, probs)}}
            else:
                probs = torch.softmax(logp[idx[0]][self.digit_ids[:len(extra)]], 0).tolist()
                answers[name] = {"type": "score", "score": round(sum(i * p for i, p in enumerate(probs)), 4),
                                 "confidence": round(max(probs), 4),
                                 "probabilities": {str(i): round(p, 4) for i, p in enumerate(probs)},
                                 "legend": {str(i): l for i, l in enumerate(extra)}}
        return {"model": "glimmer-30b-systemone", "version": VERSION, "answers": answers,
                "input": {"image": img is not None, "state_chars": len(state)},
                "usage": {"input_tokens": ntok * len(qs), "prompts": len(qs), "output_tokens": 0},
                "timing": {"forward_s": round(dt, 4), "total_s": round(time.time() - t_all, 4)}}

    @modal.fastapi_endpoint(method="POST", label="glimmer-decide")
    def decide(self, body: dict) -> dict:
        from fastapi import HTTPException
        try:
            return self._decide(body)
        except (ValueError, KeyError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    @modal.method()
    def decide_rpc(self, body: dict) -> dict:
        """The same call for other Modal apps. Errors come back as {"error": ...}."""
        try:
            return self._decide(body)
        except (ValueError, KeyError) as e:
            return {"error": str(e)}

    @modal.method()
    def warm(self) -> dict:
        """Wakes the container. The work happens in load()."""
        return {"ok": True, "version": VERSION, "heads": sorted(self.heads)}


@app.function(image=gpu_image, timeout=60)
@modal.fastapi_endpoint(method="GET", label="glimmer-health")
def health():
    return {"ok": True, "version": VERSION}
