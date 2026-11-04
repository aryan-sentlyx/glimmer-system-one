"""Latency race from the Mac: Muse Spark JSON (default and low) against the Glimmer decision API.

Same images, same three questions, round trips measured from this machine.
Usage: cd src && uv run python latency_race.py [--n 20]
Writes ../../results/latency_race.jsonl and prints a table.
"""
import base64, glob, io, json, os, statistics as st, sys, time
import requests
from PIL import Image
from bench_spark import call_spark

URL = "https://aryan-59489--glimmer-decide.us-east.modal.run"
DEFECTS = ["broken_large", "broken_small", "contamination"]
N = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 20


def glimmer(img):
    im = img.copy(); im.thumbnail((448, 448)); buf = io.BytesIO(); im.save(buf, format="PNG")
    body = {"state": "", "object": "bottle", "image": base64.b64encode(buf.getvalue()).decode(), "questions": {
        "defective": {"type": "noul", "instructions": "The part has a visible manufacturing defect.", "head": "noul_defective_known_L52"},
        "defect_type": {"type": "choice", "instructions": "Which defect does the part show?", "gate": "defective",
                        "criteria": {d: None for d in ["good"] + DEFECTS}},
        "severity": {"type": "score", "instructions": "How severe is the damage?", "criteria": ["none", "minor", "moderate", "severe"]}}}
    t0 = time.time(); r = requests.post(URL, json=body, timeout=300); dt = time.time() - t0
    d = r.json(); a = d["answers"]
    return {"p_defective": a["defective"]["noul"], "choice": a["defect_type"]["choice"], "severity": a["severity"]["score"],
            "latency_s": dt, "server_s": d["timing"]["total_s"]}


def main():
    files = sorted(glob.glob("../../data/latency_set/*.png"))[:N]
    # warm-up so the cold start is not inside the race
    img0 = Image.open(files[0]).convert("RGB")
    for attempt in range(8):
        try:
            glimmer(img0); break
        except Exception as e:
            print("warm-up wait", attempt, str(e)[:80]); time.sleep(10)
    call_spark(img0, "bottle", DEFECTS, "default")
    rows = []
    for f in files:
        img = Image.open(f).convert("RGB"); label = int(f[:-4].split("_")[-1]); defect = os.path.basename(f).split("_", 2)[2].rsplit("_", 1)[0]
        rec = {"file": os.path.basename(f), "label": label, "defect": defect}
        for effort in ("default", "low"):
            try:
                parsed, usage, dt, _ = call_spark(img, "bottle", DEFECTS, effort)
                rec[f"spark_{effort}"] = {"latency_s": dt, "p_defective": parsed.get("p_defective") if parsed else None,
                                         "choice": parsed.get("defect_type") if parsed else None,
                                         "out_tokens": usage.completion_tokens,
                                         "reasoning_tokens": getattr(getattr(usage, "completion_tokens_details", None), "reasoning_tokens", None)}
            except Exception as e:
                rec[f"spark_{effort}"] = {"error": str(e)[:200]}
        try:
            rec["glimmer"] = glimmer(img)
        except Exception as e:
            rec["glimmer"] = {"error": str(e)[:200]}
        print(f"{rec['file']:40s} spark_default {rec['spark_default'].get('latency_s', -1):6.2f}s  spark_low {rec['spark_low'].get('latency_s', -1):6.2f}s  "
              f"glimmer {rec['glimmer'].get('latency_s', -1):5.2f}s (server {rec['glimmer'].get('server_s', -1):.2f}s)", flush=True)
        rows.append(rec)
    with open("../../results/latency_race.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print("\n| system | n | p50 round trip | p90 round trip | server time p50 | acc (defective) |\n|---|---|---|---|---|---|")
    for k in ("spark_default", "spark_low", "glimmer"):
        ok = [r for r in rows if "latency_s" in r[k]]
        lat = sorted(r[k]["latency_s"] for r in ok)
        acc = sum(((r[k]["p_defective"] or 0) >= 0.5) == bool(r["label"]) for r in ok) / max(len(ok), 1)
        srv = st.median([r[k]["server_s"] for r in ok]) if k == "glimmer" and ok else float("nan")
        print(f"| {k} | {len(ok)} | {st.median(lat):.2f}s | {lat[int(0.9 * (len(lat) - 1))]:.2f}s | {srv:.2f}s | {acc:.0%} |")


if __name__ == "__main__":
    main()
