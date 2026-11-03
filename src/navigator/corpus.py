"""Corpus pipeline: download official PDFs, extract text, split into Article/Section chunks.

Usage:
    python -m navigator.corpus fetch      # download PDFs into data/corpus/raw/
    python -m navigator.corpus build      # parse PDFs -> data/corpus/processed/chunks.jsonl
    python -m navigator.corpus stats      # sanity-check counts per source

Design choice (D12): one chunk = one Article (Labour Law) or Section (ADGM),
so a citation like [UAE-LL Art 29] can be checked automatically against the gold answer.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "corpus" / "raw"
PROCESSED = ROOT / "data" / "corpus" / "processed"
SOURCES = ROOT / "config" / "sources.yaml"
MAX_CHARS = 3500  # long articles are split into parts that keep the same label

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def load_sources() -> list[dict]:
    return yaml.safe_load(SOURCES.read_text(encoding="utf-8"))["sources"]


# ---------------------------------------------------------------- fetch
def fetch() -> None:
    import urllib.request

    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for src in load_sources():
        out = RAW / f"{src['id']}.pdf"
        if out.exists() and out.stat().st_size > 10_000:
            print(f"✓ {src['id']} already downloaded")
            continue
        for url in src["urls"]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research benchmark)"})
                data = urllib.request.urlopen(req, timeout=60).read()
                if not data.startswith(b"%PDF"):
                    raise ValueError("response is not a PDF")
                out.write_bytes(data)
                manifest[src["id"]] = {"url": url, "downloaded": dt.date.today().isoformat(), "bytes": len(data)}
                print(f"✓ {src['id']} <- {url[:80]}…")
                break
            except Exception as e:  # try next mirror
                print(f"  ✗ {src['id']} mirror failed ({e})")
        else:
            print(f"!! Could not download {src['id']}. Download it manually from one of:\n   "
                  + "\n   ".join(src["urls"]) + f"\n   and save it as {out}")
    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------- parse
def pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    pages = [p.extract_text() or "" for p in PdfReader(str(path)).pages]
    return "\n".join(pages)


def normalize(text: str, lang: str) -> str:
    # NFKC folds Arabic presentation forms (common in PDF extraction) back to normal letters
    text = unicodedata.normalize("NFKC", text)
    if lang == "ar":
        text = text.translate(AR_DIGITS)
        text = text.replace("ـ", "")  # tatweel
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


# Headings: "Article (29)" / "Article 29" ; Arabic "المادة (29)" (PDFs often flip brackets: ")29(")
EN_ARTICLE = re.compile(r"^\s*Article\s*\(?\s*(\d{1,3})\s*\)?\s*$", re.M | re.I)
AR_ARTICLE = re.compile(r"^\s*المادة\s*[\(\)]?\s*(\d{1,3})\s*[\(\)]?\s*$", re.M)
# ADGM: "29. Sick leave" at line start
ADGM_SECTION = re.compile(r"^\s*(\d{1,3})\.\s+([A-Z][A-Za-z ,’'\-()/&]{2,90})\s*$", re.M)


def split_articles(text: str, pattern: re.Pattern, src: dict) -> list[dict]:
    """Split on headings. Numbering that restarts (e.g. 74 -> 1) marks a new part
    (the MOHRE consolidated PDF appends the Executive Regulation after the law)."""
    matches = list(pattern.finditer(text))
    chunks, part, last_num, seen = [], "law", 0, set()
    for i, m in enumerate(matches):
        num = int(m.group(1))
        if num + 20 < last_num:  # numbering restarted
            part = "exec_reg" if part == "law" else f"{part}+"
        last_num = num
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        title = m.group(2).strip() if m.lastindex and m.lastindex >= 2 else body.split("\n", 1)[0][:90]
        if len(body) < 15:  # table-of-contents line, not a real article
            continue
        key = (part, num)
        if key in seen:  # duplicate heading (e.g. ToC then body): keep the longer one
            prev = next(c for c in chunks if (c["part"], c["number"]) == key)
            if len(body) > len(prev["text"]):
                prev["text"] = body
            continue
        seen.add(key)
        chunks.append({"part": part, "number": num, "title": title, "text": body})
    return chunks


def label(src: dict, number: int, part: str) -> str:
    unit = "Art" if src["unit"] == "Article" else "s"
    prefix = src["short"] if part == "law" else f"{src['short']}-ExecReg"
    return f"{prefix} {unit} {number}"


def build() -> list[dict]:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = []
    for src in load_sources():
        pdf = RAW / f"{src['id']}.pdf"
        if not pdf.exists():
            print(f"!! missing {pdf.name}; run `python -m navigator.corpus fetch` first")
            continue
        text = normalize(pdf_text(pdf), src["lang"])
        if src["unit"] == "Section":
            pattern = ADGM_SECTION
        else:
            pattern = AR_ARTICLE if src["lang"] == "ar" else EN_ARTICLE
        for c in split_articles(text, pattern, src):
            lab = label(src, c["number"], c["part"])
            pieces = [c["text"][i:i + MAX_CHARS] for i in range(0, len(c["text"]), MAX_CHARS)]
            for j, piece in enumerate(pieces):
                out.append({
                    "id": f"{src['id']}:{c['part']}:{c['number']}:{j}",
                    "label": lab,
                    "source_id": src["id"],
                    "jurisdiction": src["jurisdiction"],
                    "lang": src["lang"],
                    "part": c["part"],
                    "number": c["number"],
                    "title": c["title"],
                    "text": piece,
                })
    path = PROCESSED / "chunks.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(out)} chunks -> {path}")
    return out


def load_chunks(path: Path | None = None) -> list[dict]:
    path = path or PROCESSED / "chunks.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def stats() -> None:
    chunks = load_chunks()
    c = Counter((r["source_id"], r["part"]) for r in chunks)
    for (sid, part), n in sorted(c.items()):
        nums = sorted({r["number"] for r in chunks if r["source_id"] == sid and r["part"] == part})
        missing = sorted(set(range(1, max(nums) + 1)) - set(nums))
        print(f"{sid:12} {part:10} chunks={n:4}  units={len(nums):3}  max={max(nums):3}  missing={missing[:15]}")
    print("\nExpect roughly: Labour Law law-part ≈ 74 articles (EN and AR); ADGM ER 2024 ≈ 75 sections.")
    print("Missing numbers usually mean a heading the regex didn't catch: check that page in the PDF.")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    {"fetch": fetch, "build": build, "stats": stats}[cmd]()
