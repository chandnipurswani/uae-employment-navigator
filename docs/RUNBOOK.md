# Runbook: from zero to results

Written for a first run. About 2–3 hours of hands-on time, spread over a few sessions.
**Cost estimate:** Claude + GPT judge ≈ a few dollars; Colab Pro compute ≈ $10.

## 0. One-time setup (laptop)

1. Install Python 3.11+ (python.org) and Git.
2. Clone your repo and install:
   ```bash
   git clone https://github.com/chandnipurswani/uae-employment-navigator.git
   cd uae-employment-navigator
   python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
   pip install -e ".[embeddings,dev]"
   ```
3. Copy `.env.example` to `.env` and fill in your keys. Then load them before each session:
   ```bash
   export $(cat .env | xargs)     # Windows PowerShell: set each one with $env:NAME="value"
   ```
4. Check everything works without keys: `pytest -q` should show all tests passing.

## 1. Build the corpus (~5 min)

```bash
python -m navigator.corpus fetch    # downloads the official PDFs
python -m navigator.corpus build    # splits them into Articles / Sections
python -m navigator.corpus stats    # sanity check
```
If a download fails, the script prints the official URLs. Download the PDF in your browser and save it with the name it asks for, in `data/corpus/raw/`.

**Check:** `stats` should show about 74 articles for each Labour Law language and about 75 ADGM sections. Missing numbers mean a heading didn't parse: tell Claude which ones and it will adjust the pattern.

## 2. Verify the gold answers (~30 min, the part only you can do)

```bash
python -m navigator.verify_gold
```
- ✓ = the key facts were found in the cited article.
- ✗ = check that question. Usually the article number is off (laws get renumbered by amendments) or the wording differs. Fix it in `data/build_questions.py`, run `python data/build_questions.py`, then verify again.
- Then **read every ✓ item** against the article text. For each one you agree with, set `"human_ok": true` in `data/gold_verification.json`. Only those count as `verified`.

## 3. Retrieve passages once, for every model (~5 min)

```bash
python -m navigator.retrieve
```
This writes `results/retrieval.jsonl` (the exact passages every model will see) and prints retrieval recall.

## 4. Run Claude (~5 min)

```bash
python -m navigator.run --models claude-sonnet
```

## 5. Run Jais and Falcon on Colab Pro (~1 hour)

1. Open `notebooks/run_open_models.ipynb` in Colab (File → Upload notebook).
2. Runtime → Change runtime type → **L4** (or A100).
3. Add `HF_TOKEN` in the 🔑 Secrets panel. First accept each model's licence on its Hugging Face page while logged in.
4. Upload your `results/retrieval.jsonl` when asked, then Run all.
5. Download `jais-2-8b.jsonl` and `falcon-h1-7b.jsonl` from the Drive folder into `results/answers/` on your laptop.
6. Write down the GPU type and its cost per hour, and put it in `config/models.yaml` (`gpu_usd_per_hour`).

## 6. Score and report (~10 min)

Add the current per-token prices for Claude in `config/models.yaml`, then:
```bash
python -m navigator.score --models claude-sonnet jais-2-8b falcon-h1-7b
python -m navigator.report
```
Read `results/summary.md`.

## 7. Human checks on the judge (~45 min)

```bash
python -m navigator.review make
```
- Open `results/review/accuracy_spotcheck.csv` in Excel or Sheets and grade 15 answers 0/1/2. Don't look at `_answer_key.json`.
- Send `results/review/arabic_review.csv` to your native Arabic reviewer (fluency 1–5).
- Save both as CSV with the same names, then:
```bash
python -m navigator.review calibrate
python -m navigator.report
```

## 8. Write it up

Fill in the Results section of the README from `results/summary.md`, including the recommendation and the calibration numbers. Then flip the repo to public (GitHub → Settings → General → Danger zone → Change visibility).

## Demo

```bash
streamlit run app/streamlit_app.py
```
