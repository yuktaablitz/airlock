"""Uncertainty and calibration for the classifier eval (test split, thresholds from dev).

- 95% bootstrap CIs (2,000 resamples of test rows) for F1 and for false-positive rates.
- Exact McNemar tests on paired per-row correctness: is one system's advantage more than noise?
- Calibration of Drex's chunk probabilities: a chunk's label is 1 if it overlaps the injected span.
  Expected calibration error (10 equal-width bins) + reliability diagram. Drex claims calibrated
  probabilities; thresholds only mean something if that holds.

    AIRLOCK_CRITERIA=v3 python -m eval.stats
"""

from __future__ import annotations

import json
from math import comb

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from eval.report import RUNS, TAG, airlock_decide, load

SYSTEMS = {"baseline": "LLM guard", "drex": "Drex only", "airlock": "Airlock recall"}


def predictions(rows: list[dict], th: dict) -> dict[str, np.ndarray]:
    return {
        "baseline": np.array([bool(r["baseline"].get("injection")) for r in rows]),
        "drex": np.array([bool(airlock_decide(r, th["drex_only_tau"], th["drex_only_tau"])[0]) for r in rows]),
        "airlock": np.array([bool(airlock_decide(r, th["tau_low"], th["tau_high"])[0]) for r in rows]),
    }


def f1(y: np.ndarray, p: np.ndarray) -> float:
    tp, fp, fn = (p & y).sum(), (p & ~y).sum(), (~p & y).sum()
    return 2 * tp / max(2 * tp + fp + fn, 1)


def bootstrap(fn, n: int, reps: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    vals = [fn(rng.integers(0, n, n)) for _ in range(reps)]
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def mcnemar(a_correct: np.ndarray, b_correct: np.ndarray) -> dict:
    """Exact two-sided McNemar test on the discordant pairs."""
    b, c = int((a_correct & ~b_correct).sum()), int((~a_correct & b_correct).sum())
    n, k = b + c, min(b, c)
    p = min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0
    return {"a_only_right": b, "b_only_right": c, "p_value": p}


def calibration(rows: list[dict], bins: int = 10) -> dict:
    probs, labels = [], []
    for r in rows:
        span = r["injected_span"]
        for c in r["drex"].get("chunks", []):
            probs.append(c["p"])
            labels.append(int(bool(span) and c["start"] < span[1] and span[0] < c["end"]))
    p, y = np.array(probs), np.array(labels)
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    table, ece = [], 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            conf, acc = float(p[m].mean()), float(y[m].mean())
            ece += m.mean() * abs(conf - acc)
            table.append({"bin": f"{edges[b]:.1f}–{edges[b + 1]:.1f}", "n": int(m.sum()), "mean_p": conf, "frac_injected": acc})
    brier = float(((p - y) ** 2).mean())
    return {"n_chunks": len(p), "positives": int(y.sum()), "ece": float(ece), "brier": brier, "bins": table}


def main() -> None:
    rows = load()
    th = json.loads((RUNS / f"thresholds_{TAG}.json").read_text())
    test = [r for r in rows if r["split"] == "test"]
    hold = [r for r in rows if r["split"] == "holdout"]
    y = np.array([r["label"] == 1 for r in test])
    hard = np.array([r["family"] == "hard_negative" for r in test])
    pred, pred_h = predictions(test, th), predictions(hold, th)

    out = {"thresholds": th, "systems": {}}
    for k, p in pred.items():
        out["systems"][k] = {
            "f1": f1(y, p), "f1_ci": bootstrap(lambda i: f1(y[i], p[i]), len(y)),
            "fpr_hard": float(p[hard].mean()), "fpr_hard_ci": bootstrap(lambda i: p[hard][i].mean(), int(hard.sum())),
            "fpr_holdout": float(pred_h[k].mean()),
            "fpr_holdout_ci": bootstrap(lambda i: pred_h[k][i].mean(), len(hold)),
        }
    correct = {k: p == y for k, p in pred.items()}
    out["mcnemar"] = {"drex_vs_llm_guard": mcnemar(correct["drex"], correct["baseline"]),
                      "airlock_vs_llm_guard": mcnemar(correct["airlock"], correct["baseline"]),
                      "airlock_vs_drex": mcnemar(correct["airlock"], correct["drex"])}
    out["calibration"] = calibration(test)
    (RUNS / f"stats_{TAG}.json").write_text(json.dumps(out, indent=2))

    pct = lambda x: f"{100 * x:.1f}%"
    ci = lambda v, c, f=pct: f"{f(v)} [{f(c[0])}–{f(c[1])}]"
    num = lambda x: f"{x:.3f}"
    cal = out["calibration"]
    lines = [f"# Uncertainty and calibration (test n={len(test)}, holdout n={len(hold)}; criteria {TAG})", "",
             "95% bootstrap intervals, 2,000 resamples.", "",
             "| System | F1 | FPR test hard negatives | FPR held-out hard negatives |", "|---|---|---|---|"]
    for k, s in out["systems"].items():
        lines.append(f"| {SYSTEMS[k]} | {ci(s['f1'], s['f1_ci'], num)} | {ci(s['fpr_hard'], s['fpr_hard_ci'])} | "
                     f"{ci(s['fpr_holdout'], s['fpr_holdout_ci'])} |")
    lines += ["", "## Paired McNemar tests (per-row correctness, exact)", "", "| Comparison | A right, B wrong | A wrong, B right | p |",
              "|---|---|---|---|"]
    for name, m in out["mcnemar"].items():
        lines.append(f"| {name.replace('_vs_', ' vs ').replace('_', ' ')} | {m['a_only_right']} | {m['b_only_right']} | {m['p_value']:.2g} |")
    lines += ["", f"## Calibration of Drex chunk probabilities ({cal['n_chunks']} chunks, {cal['positives']} injected)", "",
              f"Expected calibration error **{cal['ece']:.3f}**, Brier score {cal['brier']:.4f}.", "",
              "| p bin | chunks | mean p | fraction injected |", "|---|---|---|---|"]
    lines += [f"| {b['bin']} | {b['n']} | {b['mean_p']:.3f} | {b['frac_injected']:.3f} |" for b in cal["bins"]]
    (RUNS / f"stats_{TAG}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    fig, ax = plt.subplots(figsize=(4.6, 4.6), dpi=150)
    xs = [b["mean_p"] for b in cal["bins"]]
    ys = [b["frac_injected"] for b in cal["bins"]]
    ns = [b["n"] for b in cal["bins"]]
    ax.plot([0, 1], [0, 1], "--", color="#999", lw=1, label="perfect calibration")
    ax.scatter(xs, ys, s=[20 + 300 * n / max(ns) for n in ns], color="#e8a317", zorder=3, label="Drex (size = chunks)")
    ax.plot(xs, ys, color="#e8a317", lw=1.5)
    ax.set_xlabel("Drex probability (bin mean)")
    ax.set_ylabel("Fraction of chunks actually injected")
    ax.set_title(f"Reliability · ECE {cal['ece']:.3f}")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(RUNS / f"calibration_{TAG}.png")


if __name__ == "__main__":
    main()
