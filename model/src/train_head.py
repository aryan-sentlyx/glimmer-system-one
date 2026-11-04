"""Train the calibrated decision head on saved Glimmer features (CPU, local).

Features: ../../data/features/<obj>.test.<side>.npy  shape (n, 4 layers, 6656) fp16, layers (13, 25, 37, 52)
Labels:   ../../results/decisions/glimmer-30b-zeroshot-<side>.test.jsonl

Two evaluations:
  1. leave-one-object-out: train on 14 objects, test on the held-out object (generalization)
  2. 5-fold random within all objects (in-domain)
Also fits temperature scaling on the zero-shot P(defective) as the cheapest calibrator.

Usage: cd src && uv run python train_head.py --side 448
"""
import argparse
import json
import os

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

LAYERS = (13, 25, 37, 52)


def ece(p, y, n_bins=10):
    bins = np.linspace(0, 1, n_bins + 1); e = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
        if m.any():
            e += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(e)


def metrics(p, y):
    return {"auroc": float(roc_auc_score(y, p)) if len(set(y)) > 1 else float("nan"),
            "acc": float(((p >= 0.5) == y).mean()), "ece": ece(p, y), "brier": float(brier_score_loss(y, p))}


def fit_temperature(logit, y):
    """1-D temperature + bias on a logit, by grid search on NLL."""
    best = (1e9, 1.0, 0.0)
    for T in np.linspace(0.2, 5, 49):
        for b in np.linspace(-3, 3, 31):
            p = 1 / (1 + np.exp(-(logit / T + b))); p = np.clip(p, 1e-6, 1 - 1e-6)
            nll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
            if nll < best[0]:
                best = (nll, T, b)
    return best[1], best[2]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--side", type=int, default=448); ap.add_argument("--C", type=float, default=0.05)
    a = ap.parse_args()
    recs = [json.loads(l) for l in open(f"../../results/decisions/glimmer-30b-zeroshot-{a.side}.test.jsonl")]
    objs = sorted({r["object"] for r in recs})
    X, y, g, pz = [], [], [], []
    for o in objs:
        f = np.load(f"../../data/features/{o}.test.{a.side}.npy").astype(np.float32)
        rs = [r for r in recs if r["object"] == o]
        assert len(rs) == len(f), (o, len(rs), len(f))
        X.append(f); y += [r["label"] for r in rs]; g += [o] * len(rs); pz += [r["p_defective"] for r in rs]
    X = np.concatenate(X); y = np.array(y); g = np.array(g); pz = np.clip(np.array(pz), 1e-6, 1 - 1e-6)
    print(f"features {X.shape}, positives {y.mean():.2f}")
    print("zero-shot      ", metrics(pz, y))

    # temperature scaling of the zero-shot probability, leave-one-object-out
    zl = np.log(pz / (1 - pz)); pt = np.zeros_like(pz)
    for o in objs:
        tr = g != o; T, b = fit_temperature(zl[tr], y[tr]); pt[~tr] = 1 / (1 + np.exp(-(zl[~tr] / T + b)))
    print("zero-shot+temp ", metrics(pt, y), "(leave-one-object-out)")

    results = {}
    for li, L in enumerate(LAYERS):
        Xl = X[:, li]
        # leave-one-object-out
        p_loo = np.zeros(len(y))
        for o in objs:
            tr = g != o
            sc = StandardScaler().fit(Xl[tr]); clf = LogisticRegression(C=a.C, max_iter=2000).fit(sc.transform(Xl[tr]), y[tr])
            p_loo[~tr] = clf.predict_proba(sc.transform(Xl[~tr]))[:, 1]
        # 5-fold random
        p_cv = np.zeros(len(y))
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=0).split(Xl, y):
            sc = StandardScaler().fit(Xl[tr]); clf = LogisticRegression(C=a.C, max_iter=2000).fit(sc.transform(Xl[tr]), y[tr])
            p_cv[te] = clf.predict_proba(sc.transform(Xl[te]))[:, 1]
        results[L] = {"loo": metrics(p_loo, y), "cv5": metrics(p_cv, y)}
        print(f"layer {L:2d} LOO {results[L]['loo']}  CV5 {results[L]['cv5']}")

    best_L = max(LAYERS, key=lambda L: results[L]["cv5"]["auroc"] - results[L]["cv5"]["ece"])
    li = LAYERS.index(best_L); Xl = X[:, li]
    sc = StandardScaler().fit(Xl); clf = LogisticRegression(C=a.C, max_iter=2000).fit(sc.transform(Xl), y)
    os.makedirs("../../results/head", exist_ok=True)
    np.savez(f"../../results/head/noul_defective_L{best_L}.npz", layer=best_L, mean=sc.mean_, scale=sc.scale_,
             coef=clf.coef_[0], intercept=clf.intercept_[0])
    json.dump({str(k): v for k, v in results.items()}, open("../../results/head/results.json", "w"), indent=1)
    print(f"saved head for layer {best_L} to ../../results/head/")


if __name__ == "__main__" and "--holdout" not in __import__("sys").argv:
    main()


def holdout_mode(side: int, C: float, frac: float, seed: int = 0):
    """Known-product mode: per object, a stratified split. Train the head on the train half,
    report on the held-out half, save the head and the held-out indices for the demo."""
    from sklearn.model_selection import train_test_split
    recs = [json.loads(l) for l in open(f"../../results/decisions/glimmer-30b-zeroshot-{side}.test.jsonl")]
    objs = sorted({r["object"] for r in recs})
    Xtr, ytr, Xte, yte, pz_te, held = [], [], [], [], [], {}
    for o in objs:
        f = np.load(f"../../data/features/{o}.test.{side}.npy").astype(np.float32)
        rs = [r for r in recs if r["object"] == o]
        y = np.array([r["label"] for r in rs]); idx = np.arange(len(rs))
        tr, te = train_test_split(idx, test_size=frac, stratify=y, random_state=seed)
        held[o] = sorted(int(i) for i in te)
        Xtr.append(f[tr]); ytr += list(y[tr]); Xte.append(f[te]); yte += list(y[te]); pz_te += [rs[i]["p_defective"] for i in te]
    Xtr = np.concatenate(Xtr); Xte = np.concatenate(Xte); ytr = np.array(ytr); yte = np.array(yte)
    pz_te = np.clip(np.array(pz_te), 1e-6, 1 - 1e-6)
    print(f"holdout {frac}: train {len(ytr)}, test {len(yte)}")
    print("zero-shot on held-out ", metrics(pz_te, yte))
    best = None
    for li, L in enumerate(LAYERS):
        sc = StandardScaler().fit(Xtr[:, li]); clf = LogisticRegression(C=C, max_iter=3000).fit(sc.transform(Xtr[:, li]), ytr)
        p = clf.predict_proba(sc.transform(Xte[:, li]))[:, 1]; m = metrics(p, yte)
        print(f"layer {L:2d} head on held-out", m)
        if best is None or m["auroc"] - m["ece"] > best[0]:
            best = (m["auroc"] - m["ece"], L, sc, clf, m)
    _, L, sc, clf, m = best
    os.makedirs("../../results/head", exist_ok=True)
    np.savez(f"../../results/head/noul_defective_known_L{L}.npz", layer=L, mean=sc.mean_, scale=sc.scale_,
             coef=clf.coef_[0], intercept=clf.intercept_[0], template="inspect_defective_v1")
    json.dump({"side": side, "frac": frac, "seed": seed, "layer": L, "metrics_heldout": m, "heldout_idx": held},
              open("../../results/head/known_split.json", "w"), indent=1)
    print(f"saved known-product head, layer {L}, metrics {m}")


if __name__ == "__main__" and "--holdout" in __import__("sys").argv:
    import sys
    i = sys.argv.index("--holdout"); holdout_mode(448, 0.05, float(sys.argv[i + 1]))
