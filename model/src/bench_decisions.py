"""Benchmark OpenRouter decision models (Jev 1.14 and others) on MVTec AD test images.

Runs on Modal CPU containers, reads the parquet files from the glimmer-data volume,
writes one JSONL per model to /data/results/decisions/<model>.jsonl.

Usage:
  cd src && uv run modal run bench_decisions.py --model typesafe/jev-1.14 --objects bottle --limit 10
  cd src && uv run modal run bench_decisions.py --model typesafe/jev-1.14 --objects all
"""
import modal
from glimmer_image import DATA_MOUNT, LOCAL_MODULES, data_vol, secrets

app = modal.App("bench-decisions")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("requests", "python-dotenv", "pillow", "pyarrow", "numpy", "scikit-learn")
         .add_local_python_source(*LOCAL_MODULES))

ALL_OBJECTS = ["bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather", "metal_nut",
               "pill", "screw", "tile", "toothbrush", "transistor", "wood", "zipper"]


@app.function(image=image, volumes={DATA_MOUNT: data_vol}, secrets=secrets, timeout=3600, cpu=2)
def run_object(model: str, obj: str, limit: int | None, seed: int) -> list[dict]:
    import time, json
    from mvtec_data import load_rows
    from decisions_client import decide, image_part, inspection_questions

    rows = load_rows(obj, "test", limit=None, seed=seed)
    defect_types = sorted({r.defect for r in rows if r.defect != "good"})
    if limit:
        rows = rows[:limit]
    qs = inspection_questions(obj.replace("_", " "), defect_types)
    out = []
    for i, r in enumerate(rows):
        state = [f"Photo of a {obj.replace('_', ' ')} from a production line, taken for quality inspection.",
                 image_part(r.image, max_side=1024)]
        rec = {"model": model, "object": obj, "idx": i, "label": r.label, "defect": r.defect,
               "defect_types": defect_types}
        for attempt in range(3):
            try:
                answers, usage, dt, raw = decide(state, qs, model=model)
                rec.update({"p_defective": answers["defective"]["noul"],
                            "choice": answers["defect_type"]["choice"],
                            "choice_probs": answers["defect_type"]["probabilities"],
                            "choice_conf": answers["defect_type"].get("confidence"),
                            "severity": answers["severity"]["score"],
                            "severity_probs": answers["severity"]["probabilities"],
                            "latency_s": dt, "input_tokens": usage.get("input_tokens"),
                            "cost_usd": usage.get("cost"), "resolved_model": raw.get("model")})
                break
            except Exception as e:
                rec["error"] = str(e)[:300]
                time.sleep(2 * (attempt + 1))
        out.append(rec)
    return out


def summarize(recs: list[dict]) -> dict:
    import numpy as np
    from sklearn.metrics import roc_auc_score, brier_score_loss
    ok = [r for r in recs if "p_defective" in r]
    if not ok:
        return {"n": 0, "errors": len(recs)}
    y = np.array([r["label"] for r in ok]); p = np.array([r["p_defective"] for r in ok])
    s = {"n": len(ok), "errors": len(recs) - len(ok),
         "noul_auroc": float(roc_auc_score(y, p)) if len(set(y)) > 1 else None,
         "noul_acc@0.5": float(((p >= 0.5) == y).mean()),
         "noul_brier": float(brier_score_loss(y, p)),
         "choice_acc": float(np.mean([r["choice"] == r["defect"] for r in ok])),
         "choice_binary_acc": float(np.mean([(r["choice"] != "good") == bool(r["label"]) for r in ok])),
         "latency_p50_s": float(np.median([r["latency_s"] for r in ok])),
         "cost_total_usd": float(sum(r.get("cost_usd") or 0 for r in ok)),
         "tokens_mean": float(np.mean([r.get("input_tokens") or 0 for r in ok]))}
    # expected calibration error, 10 bins, for the noul question
    bins = np.linspace(0, 1, 11); ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
        if m.any():
            ece += m.mean() * abs(p[m].mean() - y[m].mean())
    s["noul_ece"] = float(ece)
    return s


@app.local_entrypoint()
def main(model: str = "typesafe/jev-1.14", objects: str = "bottle", limit: int = 0, seed: int = 0):
    import json, os
    objs = ALL_OBJECTS if objects == "all" else objects.split(",")
    results = []
    for part in run_object.starmap([(model, o, limit or None, seed) for o in objs]):
        results.extend(part)
    os.makedirs("../../results/decisions", exist_ok=True)
    fname = f"../../results/decisions/{model.replace('/', '__')}{'' if objects == 'all' else '_' + objects.replace(',', '+')}.jsonl"
    with open(fname, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(results)} rows to {fname}")
    print(json.dumps(summarize(results), indent=2))
    for o in objs:
        sub = [r for r in results if r["object"] == o]
        s = summarize(sub)
        print(f"  {o:12s} n={s.get('n')} auroc={s.get('noul_auroc')} choice_acc={s.get('choice_acc')} p50={s.get('latency_p50_s')}")
