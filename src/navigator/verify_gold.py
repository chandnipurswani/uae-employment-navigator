"""Check every drafted gold answer against the official text.

For each question: every key-fact group (e.g. "30|ثلاثين") must appear in the text of at least
one cited Article/Section. Pass -> "auto_verified". Fail -> "needs_review" + the reason.
A human then reads the auto_verified items and marks them "verified" in
data/gold_verification.json (field human_ok: true). Nothing is "verified" without a human.

    python -m navigator.verify_gold
"""
from __future__ import annotations

import json
from pathlib import Path

from .corpus import load_chunks
from .text import normalize_for_match

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "data" / "questions.jsonl"
VERIFICATION = ROOT / "data" / "gold_verification.json"


def load_questions(with_status: bool = True) -> list[dict]:
    qs = [json.loads(l) for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]
    if with_status and VERIFICATION.exists():
        ver = json.loads(VERIFICATION.read_text(encoding="utf-8"))
        for q in qs:
            v = ver.get(q["id"], {})
            if v.get("human_ok") and v.get("auto") == "auto_verified":
                q["status"] = "verified"
            elif "auto" in v:
                q["status"] = v["auto"]
    return qs


def check(q: dict, chunks: list[dict]) -> tuple[str, str]:
    if q["type"] == "unanswerable":
        return "auto_verified", "unanswerable: nothing to check in text (confirm by reading)"
    if not q["key_facts"]:
        return "needs_review", "no key facts: human check only"
    # Arabic questions are checked against the Arabic Labour Law text; ADGM is English only
    texts = []
    for cite in q["gold_citations"]:
        hits = [c for c in chunks if c["label"] == cite and (c["lang"] == q["lang"] or c["jurisdiction"] == "adgm")]
        if not hits:
            hits = [c for c in chunks if c["label"] == cite]
        if not hits:
            return "needs_review", f"citation {cite} not found in corpus (parse issue or wrong number)"
        texts.append(" ".join(h["text"] for h in hits))
    blob = normalize_for_match(" ".join(texts))
    missing = [g for g in q["key_facts"]
               if not any(normalize_for_match(alt) in blob for alt in g.split("|"))]
    if missing:
        return "needs_review", f"key fact(s) {missing} not found in cited text"
    return "auto_verified", "all key facts found in cited text"


def main() -> None:
    chunks = load_chunks()
    old = json.loads(VERIFICATION.read_text(encoding="utf-8")) if VERIFICATION.exists() else {}
    out = {}
    for q in load_questions(with_status=False):
        status, reason = check(q, chunks)
        out[q["id"]] = {"auto": status, "reason": reason,
                        "human_ok": old.get(q["id"], {}).get("human_ok", False)}
        flag = "✓" if status == "auto_verified" else "✗"
        print(f"{flag} {q['id']}  {reason}")
    VERIFICATION.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    n = sum(v["auto"] == "auto_verified" for v in out.values())
    print(f"\n{n}/{len(out)} auto-verified. Fix the ✗ items in data/build_questions.py, "
          f"then set human_ok=true in {VERIFICATION.name} after reading each one.")


if __name__ == "__main__":
    main()
