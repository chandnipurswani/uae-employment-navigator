"""Shared retrieval (D8: every model gets the SAME passages).

Hybrid retriever (D13): BM25 + multilingual embeddings (BAAI/bge-m3) fused with
reciprocal-rank fusion. Embeddings are what let an Arabic question find an English
ADGM section; without sentence-transformers installed we fall back to BM25 only
(fine for tests, NOT for the real benchmark: `python -m navigator.retrieve` warns).

Jurisdiction strategy is configurable in config/run.yaml (`retrieval.strategy`).

    python -m navigator.retrieve      # -> results/retrieval.jsonl + retrieval recall report
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from rank_bm25 import BM25Okapi

from .corpus import load_chunks
from .text import tokenize
from .verify_gold import load_questions

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
RUN_CFG = ROOT / "config" / "run.yaml"


def load_run_cfg() -> dict:
    return yaml.safe_load(RUN_CFG.read_text(encoding="utf-8"))


class Retriever:
    def __init__(self, chunks: list[dict], use_embeddings: bool = True, model_name: str = "BAAI/bge-m3"):
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c["title"] + " " + c["text"]) for c in chunks])
        self.emb = None
        if use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer
                self.encoder = SentenceTransformer(model_name)
                self.emb = self.encoder.encode([c["title"] + "\n" + c["text"] for c in chunks],
                                               normalize_embeddings=True, batch_size=16, show_progress_bar=True)
            except ImportError:
                print("!! sentence-transformers not installed: BM25-only retrieval "
                      "(Arabic->English cross-lingual matches will be weak). pip install sentence-transformers")

    def rank(self, query: str, idx: list[int]) -> list[int]:
        """Return chunk indices from `idx`, best first (RRF of BM25 and embedding ranks)."""
        bm = self.bm25.get_scores(tokenize(query))
        orders = [sorted(idx, key=lambda i: -bm[i])]
        if self.emb is not None:
            qv = self.encoder.encode([query], normalize_embeddings=True)[0]
            sims = self.emb @ qv
            orders.append(sorted(idx, key=lambda i: -sims[i]))
        rrf = {i: 0.0 for i in idx}
        for order in orders:
            for r, i in enumerate(order):
                rrf[i] += 1.0 / (60 + r)
        return sorted(idx, key=lambda i: -rrf[i])

    def retrieve(self, q: dict, cfg: dict) -> list[dict]:
        k = cfg["k"]
        lang = q["lang"]
        # Mainland passages in the question's language (Arabic Labour Law is authoritative); ADGM is English only
        ml_lang = lang if cfg.get("mainland_text_lang", "match_question") == "match_question" else "en"
        mainland = [i for i, c in enumerate(self.chunks) if c["jurisdiction"] == "mainland" and c["lang"] == ml_lang]
        adgm = [i for i, c in enumerate(self.chunks) if c["jurisdiction"] == "adgm"]
        strategy = cfg["strategy"]
        if strategy == "balanced":   # always show both jurisdictions; model must say which applies
            half = k // 2
            picked = self.rank(q["question"], mainland)[:k - half] + self.rank(q["question"], adgm)[:half]
        else:                        # "open": let ranking decide across everything
            picked = self.rank(q["question"], mainland + adgm)[:k]
        seen, out = set(), []
        for i in picked:  # de-duplicate split parts of the same article
            c = self.chunks[i]
            if c["id"] in seen:
                continue
            seen.add(c["id"])
            out.append({k2: c[k2] for k2 in ("id", "label", "jurisdiction", "lang", "title", "text")})
        return out


def main() -> None:
    cfg = load_run_cfg()["retrieval"]
    chunks = load_chunks()
    r = Retriever(chunks, use_embeddings=cfg.get("embeddings", True), model_name=cfg.get("embedding_model", "BAAI/bge-m3"))
    RESULTS.mkdir(exist_ok=True)
    hits = total = 0
    with (RESULTS / "retrieval.jsonl").open("w", encoding="utf-8") as f:
        for q in load_questions():
            ctx = r.retrieve(q, cfg)
            got = {c["label"] for c in ctx}
            need = set(q["gold_citations"])
            recall = len(got & need) / len(need) if need else None
            if need:
                hits += len(got & need)
                total += len(need)
            f.write(json.dumps({"qid": q["id"], "passages": ctx, "recall": recall}, ensure_ascii=False) + "\n")
            mark = "" if recall in (None, 1.0) else f"  <- missed {sorted(need - got)}"
            print(f"{q['id']}  recall={recall}{mark}")
    print(f"\nRetrieval recall (gold citations found in top-{cfg['k']}): {hits}/{total} = {hits / max(total, 1):.0%}")
    print("Questions with missed citations can't be fully answered by ANY model: report them separately.")


if __name__ == "__main__":
    main()
