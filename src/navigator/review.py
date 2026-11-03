"""Human-in-the-loop checks on the judge (D4 accuracy spot-check, D6 native Arabic review).

    python -m navigator.review make        # create blind sheets in results/review/
    # ...fill the human_* columns in Excel/Google Sheets, save as CSV with the same name...
    python -m navigator.review calibrate   # agreement between humans and the LLM judge

Sheets are blind: reviewers see an item number, never the model name.
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

from .verify_gold import load_questions

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
REVIEW = RESULTS / "review"


def _scores() -> list[dict]:
    rows = []
    for p in sorted((RESULTS / "scores").glob("*.jsonl")):
        if p.stem == "mock":
            continue
        rows += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows


def _answers() -> dict[tuple, str]:
    out = {}
    for p in (RESULTS / "answers").glob("*.jsonl"):
        for l in p.read_text(encoding="utf-8").splitlines():
            if l.strip():
                a = json.loads(l)
                out[(a["model"], a["qid"])] = a["answer"]
    return out


def _stratified(rows: list[dict], n: int, seed: int) -> list[dict]:
    """Spread the sample evenly across models (and languages within each model)."""
    rnd = random.Random(seed)
    models = sorted({r["model"] for r in rows})
    per = max(1, n // max(len(models), 1))
    pick = []
    for m in models:
        mine = [r for r in rows if r["model"] == m]
        rnd.shuffle(mine)
        mine.sort(key=lambda r: r["lang"])  # stable: alternate languages roughly evenly
        en = [r for r in mine if r["lang"] == "en"]
        ar = [r for r in mine if r["lang"] == "ar"]
        inter = [x for pair in zip(en, ar) for x in pair] + en[len(ar):] + ar[len(en):]
        pick += inter[:per]
    rnd.shuffle(pick)
    return pick[:n]


def make(n_acc: int = 15, n_ar: int = 10) -> None:
    REVIEW.mkdir(parents=True, exist_ok=True)
    qs = {q["id"]: q for q in load_questions()}
    rows = [r for r in _scores() if not r.get("error")]
    ans = _answers()
    key = {}

    acc = _stratified(rows, n_acc, seed=7)
    with (REVIEW / "accuracy_spotcheck.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["item", "question", "gold_answer", "assistant_answer",
                    "human_accuracy (0=wrong,1=partly,2=correct)", "notes"])
        for i, r in enumerate(acc, 1):
            item = f"ACC-{i:02d}"
            key[item] = [r["model"], r["qid"]]
            q = qs[r["qid"]]
            w.writerow([item, q["question"], q["gold_answer"], ans[(r["model"], r["qid"])], "", ""])

    ar_rows = _stratified([r for r in rows if r["lang"] == "ar"], n_ar, seed=11)
    with (REVIEW / "arabic_review.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["item", "question", "assistant_answer",
                    "human_fluency (1-5: 5=natural correct MSA & terminology, 3=understandable but awkward, 1=broken/not Arabic)",
                    "understood_dialect (yes/no/n.a.)", "notes"])
        for i, r in enumerate(ar_rows, 1):
            item = f"AR-{i:02d}"
            key[item] = [r["model"], r["qid"]]
            q = qs[r["qid"]]
            w.writerow([item, q["question"], ans[(r["model"], r["qid"])], "", "", ""])

    (REVIEW / "_answer_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    print(f"Wrote {REVIEW}/accuracy_spotcheck.csv ({len(acc)} items) and arabic_review.csv ({len(ar_rows)} items).")
    print("Don't open _answer_key.json until the reviews are done: it reveals which model wrote each answer.")


def _num(x):
    try:
        return float(str(x).strip())
    except ValueError:
        return None


def calibrate() -> None:
    key = json.loads((REVIEW / "_answer_key.json").read_text(encoding="utf-8"))
    judged = {(r["model"], r["qid"]): (r.get("judge") or {}) for r in _scores()}
    lines = ["# Judge calibration (human vs LLM judge)\n"]
    for fname, hcol, jkey, tol in [("accuracy_spotcheck.csv", 4, "accuracy", 0), ("arabic_review.csv", 3, "arabic_fluency", 1)]:
        path = REVIEW / fname
        pairs = []
        with path.open(encoding="utf-8-sig") as f:
            for row in list(csv.reader(f))[1:]:
                h = _num(row[hcol])
                j = judged.get(tuple(key[row[0]]), {}).get(jkey)
                if h is not None and j is not None:
                    pairs.append((h, float(j), row[0]))
        if not pairs:
            lines.append(f"## {fname}\nNo filled-in human scores yet.\n")
            continue
        exact = sum(h == j for h, j, _ in pairs) / len(pairs)
        within = sum(abs(h - j) <= tol for h, j, _ in pairs) / len(pairs)
        bias = sum(j - h for h, j, _ in pairs) / len(pairs)
        lines.append(f"## {fname}\n- Items with both scores: {len(pairs)}\n- Exact agreement: {exact:.0%}\n"
                     + (f"- Within ±{tol}: {within:.0%}\n" if tol else "")
                     + f"- Judge bias (judge − human, avg): {bias:+.2f} ({'judge is more lenient' if bias > 0 else 'judge is stricter' if bias < 0 else 'no bias'})\n"
                     + "- Disagreements: " + (", ".join(f"{i} (human {h:g} / judge {j:g})" for h, j, i in pairs if h != j) or "none") + "\n")
    (REVIEW / "calibration.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    {"make": make, "calibrate": calibrate}[sys.argv[1] if len(sys.argv) > 1 else "make"]()
