"""Demo: browse the benchmark side by side, and (optionally) ask Claude a new question live.

    streamlit run app/streamlit_app.py
"""
import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"

st.set_page_config(page_title="UAE Employment Navigator: model comparison", layout="wide")
st.title("UAE Employment Navigator")
st.caption("Which model should power a bilingual employment-rules assistant? Same passages, same prompt, three models. "
           "Not legal advice.")


def jl(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


qs = {q["id"]: q for q in jl(ROOT / "data" / "questions.jsonl")}
answers = {p.stem: {a["qid"]: a for a in jl(p)} for p in sorted((RES / "answers").glob("*.jsonl")) if p.stem != "mock"} \
    if (RES / "answers").exists() else {}
scores = {p.stem: {s["qid"]: s for s in jl(p)} for p in sorted((RES / "scores").glob("*.jsonl")) if p.stem != "mock"} \
    if (RES / "scores").exists() else {}
retrieval = {r["qid"]: r for r in jl(RES / "retrieval.jsonl")}

tab1, tab2, tab3 = st.tabs(["Scorecard", "Compare answers", "Ask live"])

with tab1:
    if (RES / "summary.md").exists():
        if (RES / "scorecard.png").exists():
            st.image(str(RES / "scorecard.png"))
        st.markdown((RES / "summary.md").read_text(encoding="utf-8"))
    else:
        st.info("No results yet. Run the pipeline (see docs/RUNBOOK.md).")

with tab2:
    c1, c2, c3 = st.columns(3)
    lang = c1.selectbox("Language", ["all", "en", "ar"])
    kind = c2.selectbox("Question type", ["all", "factual", "comparison", "unanswerable"])
    pool = [q for q in qs.values() if (lang == "all" or q["lang"] == lang) and (kind == "all" or q["type"] == kind)]
    qid = c3.selectbox("Question", [q["id"] for q in pool],
                       format_func=lambda i: f"{i} · {qs[i]['question'][:60]}")
    if qid:
        q = qs[qid]
        st.markdown(f"**Question** ({q['lang'].upper()}{', Gulf dialect' if q['dialect'] else ''}, {q['type']})")
        st.markdown(f"> {q['question']}")
        with st.expander(f"Gold answer · {', '.join(q['gold_citations']) or 'should decline'} · status: {q['status']}"):
            st.write(q["gold_answer"])
        if qid in retrieval:
            with st.expander("Passages every model saw"):
                for p in retrieval[qid]["passages"]:
                    st.markdown(f"**[{p['label']}]** {p['title']}")
                    st.caption(p["text"][:600] + ("…" if len(p["text"]) > 600 else ""))
        cols = st.columns(max(len(answers), 1))
        for col, (mid, ans) in zip(cols, answers.items()):
            a, s = ans.get(qid, {}), scores.get(mid, {}).get(qid, {})
            j = s.get("judge") or {}
            col.subheader(mid)
            col.markdown(a.get("answer") or f"_{a.get('error', 'no answer')}_")
            col.caption(f"judge accuracy {j.get('accuracy', '–')}/2 · citations {s.get('citations', [])} · "
                        f"{a.get('latency_s', '–')}s" + (f" · Arabic fluency {j.get('arabic_fluency')}/5" if j.get("arabic_fluency") else ""))
            if j.get("rationale"):
                col.caption(f"Judge: {j['rationale']}")

with tab3:
    st.write("Ask a new question. Retrieval + prompt are identical to the benchmark. Requires `ANTHROPIC_API_KEY` "
             "and a built corpus. (Open models need the Colab server.)")
    question = st.text_input("Your question (English or Arabic)")
    if st.button("Ask") and question:
        import sys
        sys.path.insert(0, str(ROOT / "src"))
        from navigator.corpus import load_chunks
        from navigator.models import call, load_models
        from navigator.prompts import SYSTEM, build_user_message
        from navigator.retrieve import Retriever, load_run_cfg
        from navigator.text import arabic_ratio

        cfg = load_run_cfg()

        @st.cache_resource
        def get_retriever():
            return Retriever(load_chunks(), use_embeddings=cfg["retrieval"]["embeddings"])

        passages = get_retriever().retrieve(
            {"question": question, "lang": "ar" if arabic_ratio(question) > 0.5 else "en"}, cfg["retrieval"])
        r = call(load_models()["claude-sonnet"], SYSTEM, build_user_message(question, passages),
                 cfg["generation"]["temperature"], cfg["generation"]["max_tokens"])
        st.markdown(r.text or r.error)
        st.caption(f"{r.latency_s:.1f}s · passages: " + ", ".join(p["label"] for p in passages))
