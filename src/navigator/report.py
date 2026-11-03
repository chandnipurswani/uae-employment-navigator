"""Aggregate scores into the model-selection view (D10 weights + per-use-case winners).

    python -m navigator.report                 # all scored models
    python -m navigator.report --include-mock  # include the pipeline-test model

Output: results/summary.md, results/summary.csv, results/scorecard.png
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

import yaml

from .models import load_models
from .retrieve import load_run_cfg

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"


def component_scores(r: dict) -> dict:
    """Turn one scored answer into 0-1 component scores."""
    j = r.get("judge") or {}
    has_judge = bool(j)
    if r.get("error"):
        return {"acc": 0.0, "cit": 0.0 if r["type"] != "unanswerable" else None,
                "ar": 0.0 if r["lang"] == "ar" else None, "refused": False, "juris": False}
    if r["type"] == "unanswerable":
        refused = j.get("refused") if has_judge else r["auto_refused"]
        acc = j["accuracy"] / 2 if has_judge else float(bool(refused))
        cit = None
    else:
        refused = j.get("refused", r["auto_refused"])
        acc = j["accuracy"] / 2 if has_judge else (r["key_fact"] if r["key_fact"] is not None else 0.0)
        rec = r["cite_recall"] or 0.0
        sup = (j.get("citation_support") or 0) / 2 if has_judge else rec
        cit = 0.0 if not r["citations"] else 0.5 * rec + 0.5 * sup
    ar = None
    if r["lang"] == "ar":
        in_ar = (r["arabic_ratio"] or 0) >= 0.6
        if has_judge:
            ar = ((j.get("arabic_fluency") or 1) - 1) / 4 if in_ar else 0.0
        else:
            ar = None if in_ar else 0.0  # can't judge fluency without the judge; only "not Arabic" is certain
    return {"acc": acc, "cit": cit, "ar": ar, "refused": bool(refused), "juris": j.get("jurisdiction_ok")}


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def aggregate(rows: list[dict], model: dict) -> dict:
    comp = [(r, component_scores(r)) for r in rows]
    def acc_where(f):
        return mean([c["acc"] for r, c in comp if f(r)])
    unans = [(r, c) for r, c in comp if r["type"] == "unanswerable"]
    lat = [r["latency_s"] for r in rows if not r.get("error")]
    tin = mean([r["tokens_in"] for r in rows]) or 0
    tout = mean([r["tokens_out"] for r in rows]) or 0
    cost_1k = None
    if model.get("price_in_per_m") is not None:
        cost_1k = 1000 * (tin * model["price_in_per_m"] + tout * model["price_out_per_m"]) / 1e6
    elif model.get("gpu_usd_per_hour") is not None and lat:
        cost_1k = 1000 * st.median(lat) * model["gpu_usd_per_hour"] / 3600  # sequential, no batching: conservative
    kf_pairs = [(r["key_fact"], (r.get("judge") or {}).get("accuracy")) for r in rows
                if r["key_fact"] is not None and r.get("judge")]
    agree = mean([float((kf == 1.0) == (ja == 2)) for kf, ja in kf_pairs]) if kf_pairs else None
    return {
        "model": rows[0]["model"], "display": model.get("display", rows[0]["model"]), "n": len(rows),
        "errors": sum(bool(r.get("error")) for r in rows),
        "accuracy": mean([c["acc"] for _, c in comp]),
        "acc_en": acc_where(lambda r: r["lang"] == "en" and r["type"] != "unanswerable"),
        "acc_ar": acc_where(lambda r: r["lang"] == "ar" and r["type"] != "unanswerable"),
        "acc_dialect": acc_where(lambda r: r["dialect"] and r["type"] != "unanswerable"),
        "acc_comparison": acc_where(lambda r: r["type"] == "comparison"),
        "hallucination_rate": mean([0.0 if c["refused"] else 1.0 for _, c in unans]),
        "false_refusal_rate": mean([1.0 if c["refused"] else 0.0 for r, c in comp if r["type"] != "unanswerable"]),
        "citations": mean([c["cit"] for _, c in comp]),
        "fabricated_citation_rate": mean([1.0 if r["cite_fabricated"] else 0.0 for r in rows if not r.get("error")]),
        "jurisdiction_ok": mean([float(c["juris"]) for _, c in comp if c["juris"] is not None]),
        "arabic": mean([c["ar"] for _, c in comp]),
        "replied_in_arabic": mean([float((r["arabic_ratio"] or 0) >= 0.6) for r in rows if r["lang"] == "ar" and not r.get("error")]),
        "latency_median_s": st.median(lat) if lat else None,
        "cost_per_1k_usd": cost_1k,
        "keyfact_judge_agreement": agree,
        "judged": all(r.get("judge") for r in rows if not r.get("error")),
    }


def add_cost_speed(aggs: list[dict]) -> None:
    """Min-max normalise (lower is better) across models; latency always, cost when every model has it."""
    def norm(key):
        vals = [a[key] for a in aggs]
        if any(v is None for v in vals) or len(vals) < 2 or max(vals) == min(vals):
            return None
        lo, hi = min(vals), max(vals)
        return [1 - (v - lo) / (hi - lo) for v in vals]
    lat, cost = norm("latency_median_s"), norm("cost_per_1k_usd")
    for i, a in enumerate(aggs):
        parts = [x[i] for x in (lat, cost) if x is not None]
        a["cost_speed"] = sum(parts) / len(parts) if parts else 1.0
        a["cost_speed_basis"] = "latency+cost" if cost else "latency only (fill prices in config/models.yaml)"


def pct(x):
    return "n/a" if x is None else f"{x:.0%}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-mock", action="store_true")
    args = ap.parse_args()
    cfg = load_run_cfg()
    w, cap = cfg["weights"], cfg["guardrail"]["max_hallucination_rate"]
    models = load_models()
    aggs = []
    for p in sorted((RESULTS / "scores").glob("*.jsonl")):
        if p.stem == "mock" and not args.include_mock:
            continue
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        aggs.append(aggregate(rows, models.get(p.stem, {})))
    if not aggs:
        raise SystemExit("no scores found: run navigator.score first")
    add_cost_speed(aggs)
    for a in aggs:
        a["weighted"] = (w["accuracy"] * a["accuracy"] + w["citations"] * (a["citations"] or 0)
                         + w["arabic"] * (a["arabic"] or 0) + w["cost_speed"] * a["cost_speed"])
        a["deployable"] = a["hallucination_rate"] is not None and a["hallucination_rate"] <= cap
    aggs.sort(key=lambda a: -a["weighted"])

    rec_path = RESULTS / "retrieval.jsonl"
    recs = [json.loads(l)["recall"] for l in rec_path.read_text(encoding="utf-8").splitlines()] if rec_path.exists() else []
    recall = mean([r for r in recs if r is not None])

    L = ["# Results: which model should power the UAE Employment Navigator?\n"]
    if not all(a["judged"] for a in aggs):
        L.append("> ⚠️ Some answers have no LLM-judge scores: accuracy falls back to the key-fact check. Treat as preliminary.\n")
    L.append(f"Retrieval recall (gold article in the passages every model saw): **{pct(recall)}**. "
             "Misses here cap every model equally.\n")
    L.append(f"## Weighted scorecard (accuracy {w['accuracy']:.0%} · citations {w['citations']:.0%} · "
             f"Arabic {w['arabic']:.0%} · cost/speed {w['cost_speed']:.0%})\n")
    L.append("| Rank | Model | Weighted | Accuracy | Hallucination on unanswerable | Citations | Arabic | Median latency | Cost / 1k answers | Guardrail |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for i, a in enumerate(aggs, 1):
        cost = "n/a" if a["cost_per_1k_usd"] is None else f"${a['cost_per_1k_usd']:.2f}"
        lat = "n/a" if a["latency_median_s"] is None else f"{a['latency_median_s']:.1f}s"
        L.append(f"| {i} | {a['display']} | **{a['weighted']:.2f}** | {pct(a['accuracy'])} | {pct(a['hallucination_rate'])} | "
                 f"{pct(a['citations'])} | {pct(a['arabic'])} | {lat} | {cost} | {'✅' if a['deployable'] else '⚠️ needs guardrails'} |")
    L.append(f"\nCost/speed basis: {aggs[0]['cost_speed_basis']}. Guardrail: hallucination on unanswerable questions ≤ {cap:.0%}.\n")

    L.append("## Where each model wins (no weights)\n")
    L.append("| Use case | Metric | " + " | ".join(a["display"] for a in aggs) + " | Best |")
    L.append("|---|---|" + "---|" * len(aggs) + "---|")
    slices = [("English questions", "acc_en", True), ("Arabic (MSA + dialect)", "acc_ar", True),
              ("Gulf dialect", "acc_dialect", True), ("Mainland vs ADGM comparisons", "acc_comparison", True),
              ("Knows when to say 'not covered'", "hallucination_rate", False),
              ("Over-refusal on answerable Qs", "false_refusal_rate", False),
              ("Handles jurisdiction correctly", "jurisdiction_ok", True),
              ("Replies in Arabic to Arabic Qs", "replied_in_arabic", True),
              ("Invented citation labels", "fabricated_citation_rate", False)]
    for name, key, higher in slices:
        vals = [a[key] for a in aggs]
        valid = [(v, a["display"]) for v, a in zip(vals, aggs) if v is not None]
        best = (max(valid) if higher else min(valid))[1] if valid else "n/a"
        L.append(f"| {name} | {key} | " + " | ".join(pct(v) for v in vals) + f" | {best} |")

    L.append("\n## Trust checks\n")
    for a in aggs:
        L.append(f"- {a['display']}: key-fact check agrees with judge on {pct(a['keyfact_judge_agreement'])} of answers; "
                 f"{a['errors']} errored answers.")
    cal = RESULTS / "review" / "calibration.md"
    L.append("- Human calibration: " + ("see results/review/calibration.md" if cal.exists() else
             "not done yet (run `python -m navigator.review make`)"))
    (RESULTS / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    import csv
    with (RESULTS / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(aggs[0].keys()))
        wr.writeheader()
        wr.writerows(aggs)
    try:
        _chart(aggs)
    except Exception as e:
        print("chart skipped:", e)
    print("\n".join(L))


def _chart(aggs: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    metrics = [("Accuracy", "accuracy"), ("Citations", "citations"), ("Arabic", "arabic"),
               ("Safe refusal", None), ("Cost/speed", "cost_speed")]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    width = 0.8 / len(aggs)
    colors = ["#2a78d6", "#d68a2a", "#3a9a5b", "#8a5cc2"]
    for i, a in enumerate(aggs):
        vals = [(1 - a["hallucination_rate"]) if k is None and a["hallucination_rate"] is not None else (a[k] or 0) if k else 0
                for _, k in metrics]
        ax.bar([x + i * width for x in range(len(metrics))], vals, width, label=a["display"], color=colors[i % 4])
    ax.set_xticks([x + width * (len(aggs) - 1) / 2 for x in range(len(metrics))])
    ax.set_xticklabels([m for m, _ in metrics])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Score (0–1, higher is better)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=len(aggs))
    ax.set_title("UAE Employment Navigator: model scorecard", loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(RESULTS / "scorecard.png", dpi=160)


if __name__ == "__main__":
    main()
