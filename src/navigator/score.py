"""Score answers: automatic checks + blind LLM judge (D4, D5, D6, D9).

    python -m navigator.score --models claude-sonnet jais-2-8b falcon-h1-7b
    python -m navigator.score --models mock --no-judge      # automatic checks only

Output: results/scores/<model_id>.jsonl (one row per question, judge calls cached)
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

from .retrieve import load_run_cfg
from .run import load_retrieval
from .text import arabic_ratio, normalize_for_match
from .verify_gold import load_questions

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"

CITE_RE = re.compile(r"\[\s*((?:UAE-LL|ADGM-ER)[^\]]*?)\s*\]")
REFUSAL_RE = re.compile(
    r"(do(?:es)? not (?:cover|contain|mention|specify|include)|not (?:covered|mentioned|specified|included) in|"
    r"no information|cannot find|can't find|isn't covered|aren't covered|outside the scope|"
    r"لا (?:تتضمن|تغطي|تذكر|تحدد|يتضمن|يغطي|يذكر|يحدد)|لم (?:تذكر|يذكر|تحدد|يحدد|تتضمن|يتضمن)|غير (?:مذكور|مذكورة|محدد|محددة|متوفر|متوفرة)|ليست (?:مذكورة|متوفرة)|خارج نطاق)",
    re.I)

JUDGE_PROMPT = """You are grading an answer from an AI assistant that helps UAE employees understand employment rules.
You do not know which AI system wrote it. Grade strictly and consistently. Return ONLY a JSON object.

QUESTION ({lang}{dialect}):
{question}

QUESTION TYPE: {qtype}
GOLD ANSWER (reference, written by the evaluator):
{gold}
GOLD CITATIONS: {gold_cites}

PASSAGES THE ASSISTANT WAS GIVEN:
{passages}

ASSISTANT ANSWER:
{answer}

Return JSON with these keys:
- "accuracy": 2 = all key facts correct and nothing materially wrong; 1 = partly correct (a key fact missing or a minor error); 0 = wrong, misleading, or a confident answer to an unanswerable question. For unanswerable questions: 2 = clearly says the documents don't cover it and points to an appropriate authority, 1 = declines but unhelpfully, 0 = invents an answer.
- "refused": true if the answer says the documents don't cover the question / declines to answer, else false.
- "citation_support": 2 = every cited passage actually supports the claim it is attached to; 1 = some citations don't support their claim or key claims are uncited; 0 = no citations, or citations contradict/are unrelated to the claims. Use null for unanswerable questions.
- "jurisdiction_ok": true if the answer correctly distinguishes mainland vs ADGM where that matters (or the question only concerns one and the answer uses the right one), else false.
- "arabic_fluency": ONLY if the question is in Arabic, else null. 1-5: 5 = natural, correct Modern Standard Arabic with correct legal/HR terminology and the question (including any dialect) clearly understood; 3 = understandable but awkward, translated-sounding, or with some wrong terms; 1 = not Arabic, broken, or misunderstands the question.
- "rationale": one short sentence.
"""


def extract_citations(answer: str) -> list[str]:
    out = []
    for m in CITE_RE.findall(answer):
        for part in re.split(r"[;,]\s*(?=UAE-LL|ADGM-ER)", m):
            norm = re.sub(r"\s+", " ", part.replace("Art.", "Art").replace("s.", "s")).strip()
            out.append(norm)
    return out


def key_fact_score(q: dict, answer: str) -> float | None:
    if not q["key_facts"]:
        return None
    a = normalize_for_match(answer)
    hit = sum(any(normalize_for_match(alt) in a for alt in g.split("|")) for g in q["key_facts"])
    return hit / len(q["key_facts"])


def judge(q: dict, answer: str, passages: list[dict], cfg: dict) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    ptxt = "\n\n".join(f"[{p['label']}] {p['text'][:1500]}" for p in passages)
    prompt = JUDGE_PROMPT.format(lang="Arabic" if q["lang"] == "ar" else "English",
                                 dialect=", Gulf dialect" if q["dialect"] else "", question=q["question"],
                                 qtype=q["type"], gold=q["gold_answer"], gold_cites=", ".join(q["gold_citations"]) or "none",
                                 passages=ptxt, answer=answer or "(empty answer)")
    r = client.chat.completions.create(model=cfg["model"], messages=[{"role": "user", "content": prompt}],
                                       response_format={"type": "json_object"})
    return json.loads(r.choices[0].message.content)


def score_model(model_id: str, use_judge: bool = True) -> Path:
    cfg = load_run_cfg()
    qs = {q["id"]: q for q in load_questions()}
    ctx = load_retrieval()
    answers = [json.loads(l) for l in (RESULTS / "answers" / f"{model_id}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    out = RESULTS / "scores" / f"{model_id}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    cache = {}
    if out.exists():
        for l in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(l)
            if r.get("judge"):
                cache[r["qid"]] = r["judge"]
    rows = []
    for a in answers:
        q = qs[a["qid"]]
        ans = a["answer"] or ""
        offered = {p["label"] for p in ctx[q["id"]]}
        cites = extract_citations(ans)
        gold = set(q["gold_citations"])
        row = {
            "qid": q["id"], "model": model_id, "lang": q["lang"], "dialect": q["dialect"], "type": q["type"],
            "gold_status": q["status"], "error": a.get("error"),
            "latency_s": a["latency_s"], "tokens_in": a["tokens_in"], "tokens_out": a["tokens_out"],
            "key_fact": key_fact_score(q, ans),
            "auto_refused": bool(REFUSAL_RE.search(ans)),
            "citations": cites,
            "cite_recall": (len(set(cites) & gold) / len(gold)) if gold else None,
            "cite_precision": (len(set(cites) & gold) / len(set(cites))) if (gold and cites) else (0.0 if gold else None),
            "cite_fabricated": sorted(set(cites) - offered),  # labels not in the passages it was given
            "arabic_ratio": round(arabic_ratio(ans), 2) if q["lang"] == "ar" else None,
        }
        if use_judge and not a.get("error"):
            if q["id"] not in cache:
                try:
                    cache[q["id"]] = judge(q, ans, ctx[q["id"]], cfg["judge"])
                except Exception as e:
                    print(f"  judge failed on {q['id']}: {e}")
            row["judge"] = cache.get(q["id"])
        rows.append(row)
        print(f"{model_id} {q['id']} kf={row['key_fact']} cites={cites} judge={(row.get('judge') or {}).get('accuracy')}")
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--no-judge", action="store_true")
    args = ap.parse_args()
    for m in args.models:
        score_model(m, use_judge=not args.no_judge)


if __name__ == "__main__":
    main()
