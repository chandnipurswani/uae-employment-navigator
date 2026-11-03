"""Shared text helpers for Arabic + English matching and tokenizing."""
import re
import unicodedata

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
AR_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
ARABIC_CHAR = re.compile(r"[؀-ۿ]")
LATIN_CHAR = re.compile(r"[A-Za-z]")


def normalize_for_match(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).translate(AR_DIGITS).lower()
    s = AR_DIACRITICS.sub("", s).replace("ـ", "")
    s = re.sub("[إأآٱ]", "ا", s).replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"\s+", " ", s)


def tokenize(s: str) -> list[str]:
    s = normalize_for_match(s)
    toks = re.findall(r"[a-z0-9]+|[؀-ۿ]+", s)
    out = []
    for t in toks:
        if ARABIC_CHAR.match(t) and len(t) > 4 and t.startswith("ال"):
            t = t[2:]  # light stemming: drop definite article
        out.append(t)
    return out


def arabic_ratio(s: str) -> float:
    """Share of letters that are Arabic (ignores digits, punctuation, citation labels)."""
    s = re.sub(r"\[[^\]]*\]", " ", s)  # drop [UAE-LL Art 29] style citations
    ar, la = len(ARABIC_CHAR.findall(s)), len(LATIN_CHAR.findall(s))
    return ar / (ar + la) if (ar + la) else 0.0
