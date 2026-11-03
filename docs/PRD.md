# PRD: UAE Employment Navigator: model selection for a bilingual rules assistant

**Owner:** Chandni Purswani · **Status:** v1 build · **Last updated:** Nov 2026

## 1. Problem

Employees and new hires in the UAE regularly ask practical questions about their rights: how much annual leave they get, how gratuity is calculated, what notice they must give. The answers sit in long legal texts, and they **differ depending on whether the employer is on the mainland (UAE Labour Law) or in a free zone such as ADGM (ADGM Employment Regulations 2024)**. Many of these employees ask in Arabic, often in Gulf dialect.

A team building an AI assistant for this has to answer one question before anything else: **which model should power it?** The options are a UAE sovereign open-weight model (Jais from Inception, Falcon from TII) or a frontier API model. This project answers that question with evidence instead of benchmark leaderboards.

## 2. Target user

**Primary:** employees and new hires in UAE private-sector companies (mainland and ADGM).

- They ask in plain language, in English, Modern Standard Arabic, or Gulf dialect.
- They want to know *"what does this mean for me?"*, not a legal essay.
- Being wrong hurts them. A wrong leave or gratuity figure causes real disputes, so **a confident wrong answer is worse than "I don't know, check with MOHRE/ADGM."**

**Out of scope for v1:** HR teams applying policy at scale, lawyers, and government deployments.

## 3. The decision this project supports

> For an employee-facing UAE employment-rules assistant, which model gives the best mix of accuracy, safe refusals, citation quality and Arabic quality at an acceptable cost? And where does each model win or lose?

## 4. Scope (v1)

| In | Out |
|---|---|
| UAE Labour Law (Federal Decree-Law 33/2021 and amendments), official **Arabic and English** | DIFC, DMCC and other free zones (v2) |
| ADGM Employment Regulations 2024 (English, the official language) | Executive Regulation (Cabinet Res. 1/2022), apart from what's in the MOHRE consolidated PDF |
| 40-question bilingual test set | Multi-turn chat and personal case advice |
| 3 models: Jais 2 8B Chat, Falcon-H1 7B Instruct (see D19), Claude | Fine-tuning |

## 5. Approach

1. **Same retrieval for every model.** The documents are split by Article (Labour Law) and Section (ADGM). For each question, the top passages are retrieved once, saved, and given unchanged to every model, so score differences come from the model and not the search step. Retrieval recall is reported separately, so a retrieval miss isn't blamed on a model.
2. **Same prompt for every model.** Answer from the passages only, cite `[Source, Article/Section]`, reply in the user's language, and say so when the passages don't contain the answer.
3. **Score** each answer on the metrics below.
4. **Recommend** using the weights below, and also report per-use-case winners.

## 6. Success metrics

| Metric | How it's measured | Weight |
|---|---|---|
| **Accuracy** | (a) Automatic key-fact check (e.g. answer contains "30 days"). (b) Blind LLM judge (GPT; model names hidden) grades 0/1/2 against the gold answer. (c) **Human spot-check of ~15 answers** to measure how far the judge can be trusted. | **40%** |
| **Safe refusal** | Part of accuracy: on the ~5 unanswerable questions, the model must decline and point to the authority instead of inventing an answer. Reported separately as a "hallucination rate." | (in accuracy) |
| **Citation quality** | Cites the **correct Article/Section** (automatic match to the gold reference) **and** the cited passage actually supports the claim (judge). | **25%** |
| **Arabic fluency** | On Arabic questions: (a) automatic check that the reply is in Arabic; (b) judge scores 1–5 for fluency, correct terminology, and dialect understanding; (c) **native Arabic reviewer scores ~10 answers** to check the judge. | **20%** |
| **Cost and speed** | Latency per answer and cost per 1,000 answers (API price, or GPU-hour cost for self-hosted models). | **15%** |

**Guardrail metric:** hallucination rate on unanswerable questions. Any model above 20% is flagged as "not deployable without guardrails," whatever its weighted score.

## 7. Test set design (40 questions)

- 20 English and 20 Arabic, including ~6 in Gulf dialect
- ~6 mainland-vs-ADGM comparison questions (e.g. "Do I get more annual leave in ADGM or on the mainland?")
- ~5 unanswerable questions (not covered by these documents) that should be refused
- Every question has a gold answer, gold citation(s) and key facts. **Every gold answer starts as `draft`** and becomes `verified` only after `verify_gold.py` finds the key facts in the cited article of the official text, followed by a human read-through.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| The LLM judge is wrong or biased | A different model family judges (GPT judges Claude's answers), model names are hidden, and a human spot-check reports the judge's agreement rate |
| Gold answers are wrong (legal texts get amended) | Draft/verified status, automatic fact-in-article check, and source PDFs pinned by date |
| Small open models run quantized on Colab, which may understate their quality | Quantization is recorded in results and flagged in the write-up; a full-precision rerun is a v2 item |
| Translation differences between the Arabic and English Labour Law | The Arabic text is the legally authoritative one. Arabic questions are graded against the Arabic text |

## 9. Deliverables

- Reproducible benchmark (this repo)
- Results table and charts in `results/`
- Model-selection memo: which model to use for which use case, and why
- A small demo app (Streamlit) for asking a question and comparing models side by side

## 10. Not legal advice

This is a portfolio and research project. Answers are not legal advice. Users should check with MOHRE or the ADGM Employment Affairs Office.
