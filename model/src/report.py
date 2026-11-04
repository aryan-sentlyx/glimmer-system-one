"""Merge all decision result files into one report with a reliability diagram.

Usage: cd src && uv run python report.py [--full-only]
Reads ../../results/decisions/*.jsonl, writes ../../results/report.md and ../../results/reliability.png
"""
import glob
import json
import os
import sys

import numpy as np
from bench_decisions import summarize, ALL_OBJECTS


def load(path):
    return [json.loads(l) for l in open(path)]


def main(full_only: bool):
    files = sorted(glob.glob("../../results/decisions/*.jsonl"))
    runs = {}
    for f in files:
        recs = load(f)
        if full_only and len(recs) < 1000:
            continue
        name = os.path.basename(f).replace(".jsonl", "")
        runs[name] = recs
    lines = ["# Decision models on MVTec AD (test split)\n",
             "| run | n | AUROC | acc@0.5 | ECE | Brier | type acc | p50 latency | cost |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, recs in runs.items():
        s = summarize(recs)
        lines.append(f"| {name} | {s['n']} | {s['noul_auroc']:.3f} | {s['noul_acc@0.5']:.3f} | {s['noul_ece']:.3f} | "
                     f"{s['noul_brier']:.3f} | {s['choice_acc']:.3f} | {s['latency_p50_s']:.2f}s | ${s['cost_total_usd']:.3f} |")
    full = {n: r for n, r in runs.items() if len(r) >= 1000}
    if full:
        lines += ["\n## AUROC per object\n", "| object | " + " | ".join(full) + " |", "|---|" + "---|" * len(full)]
        for o in ALL_OBJECTS:
            row = []
            for recs in full.values():
                s = summarize([r for r in recs if r["object"] == o])
                row.append(f"{s['noul_auroc']:.3f}" if s.get("noul_auroc") is not None else "-")
            lines.append(f"| {o} | " + " | ".join(row) + " |")
    md = "\n".join(lines)
    open("../../results/report.md", "w").write(md)
    print(md)
    # reliability diagram
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.plot([0, 1], [0, 1], "k--", lw=1, label="perfect")
        bins = np.linspace(0, 1, 11)
        for name, recs in (full or runs).items():
            ok = [r for r in recs if "p_defective" in r]
            p = np.array([r["p_defective"] for r in ok]); y = np.array([r["label"] for r in ok])
            xs, ys = [], []
            for lo, hi in zip(bins[:-1], bins[1:]):
                m = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
                if m.sum() >= 5:
                    xs.append(p[m].mean()); ys.append(y[m].mean())
            ax.plot(xs, ys, "o-", label=name)
        ax.set_xlabel("predicted P(defective)"); ax.set_ylabel("observed defect rate"); ax.legend(fontsize=7)
        ax.set_title("Reliability on MVTec AD"); fig.tight_layout(); fig.savefig("../../results/reliability.png", dpi=150)
        print("wrote ../../results/reliability.png")
    except Exception as e:
        print("plot failed:", e)


if __name__ == "__main__":
    main("--full-only" in sys.argv)
