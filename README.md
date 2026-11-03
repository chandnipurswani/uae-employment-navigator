# UAE Employment Navigator

**Which AI model should power a bilingual (Arabic/English) assistant that answers employees' questions about UAE employment rules?**

UAE sovereign open-weight models, **Jais 2** (Inception / G42) and **Falcon-H1-Arabic** (TII), are tested against a frontier API model (**Claude Sonnet**) on the questions employees actually ask: leave, gratuity, notice periods, and the mainland-vs-ADGM split. Answers are in English, Modern Standard Arabic and Gulf dialect.

> **Status:** pipeline built and tested; model runs in progress. Results below will be filled in from `results/summary.md`.

---

## The product question

An employee asks: *"كم يوم إجازة سنوية أستحق؟"* or *"Do I get more leave in ADGM or on the mainland?"*

The answer depends on **which law applies**: the UAE Labour Law (mainland) or the ADGM Employment Regulations 2024 (free zone). It must be **correct**, **cited**, **understandable in Arabic**, and **honest when the documents don't cover the question**.

Choosing the model is the first decision for any team building this. Public leaderboards (e.g. the Open Arabic LLM Leaderboard) measure general Arabic ability, not *"does it give an employee the right gratuity formula, with the right article, in good Arabic, without inventing anything?"* This project measures that.

## What was built

```
Official PDFs (MOHRE, ADGM)
   → split into Articles / Sections
   → same retrieved passages for every model     ← controlled experiment
   → same prompt: answer, cite, reply in the user's language, say "not covered" when it isn't
   → Claude via API · Jais 2 8B + Falcon-H1-Arabic 7B self-hosted on a GPU
   → scoring: key-fact check · blind GPT judge · citation check · Arabic check
   → human spot-checks of the judge itself
   → weighted scorecard + "where each model wins"
```

| | |
|---|---|
| **Corpus** | UAE Labour Law (Decree-Law 33/2021 + amendments), official **Arabic and English**; ADGM Employment Regulations 2024 |
| **Test set** | 40 questions: 20 English, 20 Arabic (6 in Gulf dialect), 6 mainland-vs-ADGM comparisons, 5 that **should be refused** |
| **Models** | Jais 2 8B Chat · Falcon-H1-Arabic 7B Instruct (bf16, Colab Pro) · Claude Sonnet |
| **Judge** | GPT, blind to model names (a different model family from the Claude baseline) |

## How "best" is defined

| Metric | Weight | Why it matters for this user |
|---|---|---|
| Accuracy (incl. safely declining) | 40% | A wrong leave or gratuity figure creates a real dispute |
| Citation quality | 25% | Employees, and HR, need to check the answer against the law |
| Arabic fluency | 20% | A large share of the workforce asks in Arabic, often in dialect |
| Cost and speed | 15% | Self-hosting vs API changes the economics and data residency |

**Guardrail:** any model that invents answers to more than 20% of out-of-scope questions is flagged "not deployable without guardrails", whatever its score.

The full reasoning is in **[docs/PRD.md](docs/PRD.md)**. Every product decision, with the options considered, is in **[docs/DECISIONS.md](docs/DECISIONS.md)**.

## Results

_Pending model runs._ This section will show:

- the weighted scorecard and `results/scorecard.png`
- where each model wins: English, Arabic, dialect, comparisons, refusals, citations
- how much the LLM judge agrees with human reviewers (accuracy spot-check + native Arabic review)
- **the recommendation**: which model to use for which deployment (public employee chat vs in-country/self-hosted vs HR lookup)

## How trustworthy are these results?

- **Gold answers are checked against the law, not assumed.** Each one starts as `draft`. A script confirms its key facts appear in the cited article of the official PDF, and then a human read-through marks it `verified`.
- **The judge is tested.** About 15 answers are hand-graded and about 10 Arabic answers are reviewed by a native speaker. Agreement rates are published.
- **Retrieval is reported separately**, so a search miss isn't blamed on a model.
- **Known limits:** small model sizes only (8B / 7B) in v1; 40 questions is directional, not statistically conclusive; legal texts change. Each source PDF's download date is recorded.

## Run it yourself

See **[docs/RUNBOOK.md](docs/RUNBOOK.md)** for step-by-step instructions (no prior setup assumed).

```bash
pip install -e ".[embeddings,dev]"
python -m navigator.corpus fetch && python -m navigator.corpus build
python -m navigator.verify_gold
python -m navigator.retrieve
python -m navigator.run --models claude-sonnet          # Jais/Falcon: notebooks/run_open_models.ipynb
python -m navigator.score --models claude-sonnet jais-2-8b falcon-h1-arabic-7b
python -m navigator.report
streamlit run app/streamlit_app.py
```

## Roadmap

- v2: add the large tier (Jais 2 70B, Falcon-H1-Arabic 34B) and the new **Jais 3** family (released Oct 2026)
- Add DIFC Employment Law as a third regime
- Multi-turn: ask the user which regime applies before answering

---

*Not legal advice. Built by [Chandni Purswani](https://chandnipurswani.github.io) as a product case study in model selection for sovereign Arabic AI.*
