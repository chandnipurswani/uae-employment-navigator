"""End-to-end pipeline test with a SYNTHETIC corpus and the mock model (no keys, no network).

The fixture corpus is generated from the gold answers themselves: it is NOT the real law.
It proves the plumbing (verify -> retrieve -> run -> score -> report -> review) works.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _fixture_chunks(questions):
    chunks, seen = [], set()
    for q in questions:
        for cite in q["gold_citations"]:
            juris = "adgm" if cite.startswith("ADGM") else "mainland"
            langs = ["en"] if juris == "adgm" else ["en", "ar"]
            num = int(cite.split()[-1])
            for lang in langs:
                key = (cite, lang)
                if key in seen:
                    continue
                seen.add(key)
                same = [x for x in questions if cite in x["gold_citations"] and (x["lang"] == lang or juris == "adgm")]
                text = "TEST FIXTURE, NOT LAW. " + " ".join(x["question"] + " " + x["gold_answer"] for x in same)
                chunks.append({"id": f"fx:{cite}:{lang}", "label": cite, "source_id": f"fx_{juris}_{lang}",
                               "jurisdiction": juris, "lang": lang, "part": "law", "number": num,
                               "title": cite, "text": text})
    for i in range(10):  # distractors
        for juris, lang in [("mainland", "en"), ("mainland", "ar"), ("adgm", "en")]:
            chunks.append({"id": f"fx:d{i}:{juris}:{lang}", "label": f"{'ADGM-ER s' if juris == 'adgm' else 'UAE-LL Art'} {100 + i}",
                           "source_id": "fx", "jurisdiction": juris, "lang": lang, "part": "law", "number": 100 + i,
                           "title": "Distractor", "text": "Unrelated provision about licensing fees and inspections."})
    return chunks


def _run(tmp, *args):
    env = {**os.environ, "PYTHONPATH": str(tmp / "src")}
    r = subprocess.run([sys.executable, "-m", *args], cwd=tmp, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def test_end_to_end(tmp_path):
    tmp = tmp_path / "repo"
    shutil.copytree(REPO, tmp, ignore=shutil.ignore_patterns(".git", "results", "__pycache__"))
    (tmp / "results").mkdir()
    cfg = (tmp / "config" / "run.yaml").read_text().replace("embeddings: true", "embeddings: false")
    (tmp / "config" / "run.yaml").write_text(cfg)
    qs = [json.loads(l) for l in (tmp / "data" / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
    out = tmp / "data" / "corpus" / "processed"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in _fixture_chunks(qs):
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    v = _run(tmp, "navigator.verify_gold")
    assert "auto-verified" in v
    r = _run(tmp, "navigator.retrieve")
    assert "Retrieval recall" in r
    _run(tmp, "navigator.run", "--models", "mock")
    answers = (tmp / "results" / "answers" / "mock.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(answers) == 40
    _run(tmp, "navigator.score", "--models", "mock", "--no-judge")
    rep = _run(tmp, "navigator.report", "--include-mock")
    assert "Weighted scorecard" in rep and (tmp / "results" / "summary.csv").exists()
    _run(tmp, "navigator.review", "make")
