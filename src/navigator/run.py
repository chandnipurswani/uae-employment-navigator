"""Generate answers for one or more models using the SAVED retrieval (results/retrieval.jsonl).

    python -m navigator.run --models claude-sonnet
    python -m navigator.run --models jais-2-8b          # inside the Colab notebook, with vLLM running
    python -m navigator.run --models mock               # offline pipeline test

Output: results/answers/<model_id>.jsonl (resumable: already-answered questions are skipped)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import call, load_models
from .prompts import SYSTEM, build_user_message
from .retrieve import load_run_cfg
from .verify_gold import load_questions

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"


def load_retrieval() -> dict[str, list[dict]]:
    path = RESULTS / "retrieval.jsonl"
    if not path.exists():
        raise SystemExit("results/retrieval.jsonl missing: run `python -m navigator.retrieve` first")
    return {r["qid"]: r["passages"] for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


def run(model_id: str) -> Path:
    model = load_models()[model_id]
    gen = load_run_cfg()["generation"]
    ctx = load_retrieval()
    out = RESULTS / "answers" / f"{model_id}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {json.loads(l)["qid"] for l in out.read_text(encoding="utf-8").splitlines()
                if l.strip() and not json.loads(l).get("error")}
        # keep successful lines only so failed ones are retried
        keep = [l for l in out.read_text(encoding="utf-8").splitlines() if l.strip() and not json.loads(l).get("error")]
        out.write_text("\n".join(keep) + ("\n" if keep else ""), encoding="utf-8")
    with out.open("a", encoding="utf-8") as f:
        for q in load_questions():
            if q["id"] in done:
                continue
            r = call(model, SYSTEM, build_user_message(q["question"], ctx[q["id"]]),
                     gen["temperature"], gen["max_tokens"])
            f.write(json.dumps({"qid": q["id"], "model": model_id, "answer": r.text, "latency_s": round(r.latency_s, 2),
                                "tokens_in": r.tokens_in, "tokens_out": r.tokens_out, "error": r.error},
                               ensure_ascii=False) + "\n")
            f.flush()
            print(f"{model_id} {q['id']} {'ERROR ' + r.error if r.error else f'{r.latency_s:.1f}s'}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    for m in ap.parse_args().models:
        run(m)


if __name__ == "__main__":
    main()
