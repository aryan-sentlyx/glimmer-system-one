"""Benchmark Muse Spark (Meta Model API) as a classic VLM classifier on MVTec AD: JSON output.

Same three questions as the decision models. Runs on Modal CPU containers, one per object.
Usage:
  cd src && uv run modal run bench_spark.py --objects bottle --limit 6 --effort default
  cd src && uv run modal run bench_spark.py --objects all --effort low
"""
import os
import modal
from glimmer_image import DATA_MOUNT, LOCAL_MODULES, data_vol, secrets

app = modal.App("bench-spark")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("openai", "python-dotenv", "pillow", "pyarrow", "numpy", "scikit-learn", "requests")
         .add_local_python_source(*LOCAL_MODULES))
ALL_OBJECTS = ["bottle", "cable", "capsule", "carpet", "grid", "hazelnut", "leather", "metal_nut",
               "pill", "screw", "tile", "toothbrush", "transistor", "wood", "zipper"]


def spark_prompt(obj: str, defect_types: list[str]) -> str:
    opts = ", ".join(f'"{d}"' for d in ["good"] + defect_types)
    return (f"You are a visual inspection system on a production line. Look at this photo of a {obj}.\n"
            f"Reply with JSON only, no other text, with exactly these keys:\n"
            f'{{"defective": true or false, "p_defective": number from 0 to 1 (your probability that the part has a visible '
            f'manufacturing defect), "defect_type": one of [{opts}], "severity": integer 0 to 3 (0 none, 1 minor, 2 moderate, 3 severe)}}')


def call_spark(img, obj: str, defect_types: list[str], effort: str, max_side: int = 448):
    """One Spark call. Returns (parsed dict or None, usage, seconds, raw text)."""
    import json, re, time
    from muse_client import client, image_to_data_url
    c = client()
    content = [{"type": "image_url", "image_url": {"url": image_to_data_url(img, fmt="PNG", max_side=max_side)}},
               {"type": "text", "text": spark_prompt(obj, defect_types)}]
    kw = {"model": os.environ.get("MUSE_MODEL", "muse-spark-1.3"), "messages": [{"role": "user", "content": content}],
          "response_format": {"type": "json_object"}, "max_tokens": 4096}
    if effort != "default":
        kw["reasoning_effort"] = effort
    t0 = time.time(); r = c.chat.completions.create(**kw); dt = time.time() - t0
    text = r.choices[0].message.content or ""
    try:
        parsed = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    except Exception:
        parsed = None
    return parsed, r.usage, dt, text


@app.function(image=image, volumes={DATA_MOUNT: data_vol}, secrets=secrets, timeout=3600, cpu=2)
def run_object(obj: str, limit, seed: int, effort: str) -> list[dict]:
    import time
    from mvtec_data import load_rows
    rows = load_rows(obj, "test", limit=None, seed=seed)
    defect_types = sorted({r.defect for r in rows if r.defect != "good"})
    if limit:
        rows = rows[:limit]
    out = []
    for i, r in enumerate(rows):
        rec = {"model": f"muse-spark-1.3-json-{effort}", "object": obj, "idx": i, "label": r.label,
               "defect": r.defect, "defect_types": defect_types}
        for attempt in range(3):
            try:
                parsed, usage, dt, text = call_spark(r.image, obj.replace("_", " "), defect_types, effort)
                rt = getattr(getattr(usage, "completion_tokens_details", None), "reasoning_tokens", None)
                rec.update({"latency_s": dt, "input_tokens": usage.prompt_tokens, "output_tokens": usage.completion_tokens,
                            "reasoning_tokens": rt, "raw": text[:300]})
                if parsed is None:
                    rec["error"] = "no json"; break
                p = parsed.get("p_defective"); d = parsed.get("defective")
                if not isinstance(p, (int, float)):
                    p = 1.0 if d else 0.0
                rec.update({"p_defective": float(min(max(p, 0.0), 1.0)), "choice": str(parsed.get("defect_type")),
                            "severity": parsed.get("severity"), "choice_probs": None, "choice_conf": None, "severity_probs": None})
                break
            except Exception as e:
                rec["error"] = str(e)[:300]; time.sleep(3 * (attempt + 1))
        out.append(rec)
    return out


@app.local_entrypoint()
def main(objects: str = "bottle", limit: int = 0, seed: int = 0, effort: str = "default"):
    import json
    import numpy as np
    from bench_decisions import summarize
    objs = ALL_OBJECTS if objects == "all" else objects.split(",")
    results = []
    for part in run_object.starmap([(o, limit or None, seed, effort) for o in objs]):
        results.extend(part)
        s = summarize(part); ok = [r for r in part if "latency_s" in r]
        print(f"  {part[0]['object']:12s} n={s.get('n')} err={s.get('errors')} auroc={s.get('noul_auroc')} acc={s.get('noul_acc@0.5')} "
              f"p50={s.get('latency_p50_s')} reasoning_tok={np.median([r.get('reasoning_tokens') or 0 for r in ok]) if ok else None}", flush=True)
    os.makedirs("../../results/decisions", exist_ok=True)
    tag = "" if objects == "all" else "_" + objects.replace(",", "+")
    fname = f"../../results/decisions/muse-spark-1.3-json-{effort}{tag}.jsonl"
    with open(fname, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(results)} rows to {fname}")
    s = summarize(results); ok = [r for r in results if "latency_s" in r]
    s["in_tokens_mean"] = float(np.mean([r["input_tokens"] for r in ok])) if ok else None
    s["out_tokens_mean"] = float(np.mean([r["output_tokens"] for r in ok])) if ok else None
    s["reasoning_tokens_median"] = float(np.median([r.get("reasoning_tokens") or 0 for r in ok])) if ok else None
    print(json.dumps(s, indent=2))
