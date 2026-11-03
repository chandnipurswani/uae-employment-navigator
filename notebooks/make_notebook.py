"""Generates run_open_models.ipynb (kept as code so the notebook stays reviewable in git diffs)."""
import json
from pathlib import Path

cells = [
    ("md", """# Run Jais 2 8B and Falcon-H1 7B on Colab Pro

**Decision D18:** full precision (bf16) on an **L4 or A100** GPU, so the open models are judged as released.

1. `Runtime → Change runtime type → L4 GPU` (or A100).
2. Add secrets in the 🔑 sidebar: `HF_TOKEN` (and accept the model licences on Hugging Face first).
3. Run all cells. Each model takes roughly 10–20 minutes including download. Answers are saved to your Google Drive so nothing is lost if Colab disconnects.
4. Download `results/answers/*.jsonl` and drop them into the same folder of the repo on your laptop, then score there.

The notebook uses **the same retrieval file and the same prompt** as the Claude run (D8)."""),
    ("code", """# 1) Get the repo + the shared retrieval file
REPO = "https://github.com/chandnipurswani/uae-employment-navigator.git"  # private: use a token URL or upload a zip
!git clone -q $REPO || echo "clone failed: upload the repo zip instead and unzip to /content/uae-employment-navigator"
%cd /content/uae-employment-navigator
!pip -q install -e . vllm
import os, pathlib
assert pathlib.Path("results/retrieval.jsonl").exists(), "Upload results/retrieval.jsonl from your laptop run first"
"""),
    ("code", """# 2) Save outputs to Drive (survives disconnects)
from google.colab import drive, userdata
drive.mount('/content/drive')
os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")
OUT = "/content/drive/MyDrive/uae-navigator-answers"; os.makedirs(OUT, exist_ok=True)
!nvidia-smi --query-gpu=name,memory.total --format=csv
"""),
    ("code", """# 3) Helper: start a vLLM OpenAI-compatible server for one model, run the benchmark, stop it
import subprocess, time, requests, shutil, yaml

def serve_and_run(model_id):
    m = {x["id"]: x for x in yaml.safe_load(open("config/models.yaml"))["models"]}[model_id]
    print("Serving", m["model"])
    proc = subprocess.Popen(["vllm", "serve", m["model"], "--dtype", "bfloat16", "--max-model-len", "8192",
                             "--port", "8000", "--trust-remote-code"],
                            stdout=open(f"/content/vllm_{model_id}.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(180):  # wait up to 30 min for download + load
        try:
            if requests.get("http://localhost:8000/v1/models", timeout=2).ok: break
        except Exception: pass
        time.sleep(10)
    else:
        proc.kill(); raise RuntimeError(f"server did not start, see /content/vllm_{model_id}.log")
    !python -m navigator.run --models {model_id}
    shutil.copy(f"results/answers/{model_id}.jsonl", OUT)
    proc.terminate(); proc.wait(); time.sleep(5)
    print("✓ saved to Drive:", OUT)
"""),
    ("code", "serve_and_run('jais-2-8b')"),
    ("code", "serve_and_run('falcon-h1-7b')"),
    ("md", """### If a model fails to load
- **404 / gated:** open the model page on huggingface.co while logged in and accept the licence; check the exact model id (Jais has moved between `inceptionai/` and `inception42/`) and update `config/models.yaml`.
- **Architecture not supported:** Jais 2 may need a recent vLLM; Falcon-H1 needs vLLM ≥ 0.9. `!pip install -U vllm` and retry.
- **Out of memory on L4:** lower `--max-model-len` to 4096. Don't switch to 4-bit without logging it in DECISIONS.md, because that changes D18.
- Record the GPU name and Colab compute-unit cost: the cost metric uses `gpu_usd_per_hour` in `config/models.yaml`."""),
]

nb = {"nbformat": 4, "nbformat_minor": 5,
      "metadata": {"accelerator": "GPU", "colab": {"gpuType": "L4"},
                   "kernelspec": {"name": "python3", "display_name": "Python 3"}},
      "cells": [{"cell_type": "markdown" if t == "md" else "code", "metadata": {}, "source": s,
                 **({"outputs": [], "execution_count": None} if t == "code" else {})} for t, s in cells]}
Path(__file__).with_name("run_open_models.ipynb").write_text(json.dumps(nb, indent=1), encoding="utf-8")
print("wrote run_open_models.ipynb")
