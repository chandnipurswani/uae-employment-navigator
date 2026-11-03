"""Model adapters. All return (text, usage) with the same shape so results are comparable."""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Reply:
    text: str
    latency_s: float
    tokens_in: int | None
    tokens_out: int | None
    error: str | None = None


def load_models() -> dict[str, dict]:
    cfg = yaml.safe_load((ROOT / "config" / "models.yaml").read_text(encoding="utf-8"))
    return {m["id"]: m for m in cfg["models"]}


def call(model: dict, system: str, user: str, temperature: float, max_tokens: int) -> Reply:
    t0 = time.time()
    try:
        if model["provider"] == "anthropic":
            import anthropic
            client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
            r = client.messages.create(model=model["model"], system=system, max_tokens=max_tokens,
                                       temperature=temperature, messages=[{"role": "user", "content": user}])
            text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
            return Reply(text, time.time() - t0, r.usage.input_tokens, r.usage.output_tokens)

        if model["provider"] in ("openai_compatible", "openai"):
            from openai import OpenAI
            client = OpenAI(base_url=model.get("base_url"), api_key=os.environ.get(model.get("api_key_env", "OPENAI_API_KEY"), "EMPTY"))
            r = client.chat.completions.create(model=model["model"], temperature=temperature, max_tokens=max_tokens,
                                               messages=[{"role": "system", "content": system},
                                                         {"role": "user", "content": user}])
            text = r.choices[0].message.content or ""
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()  # drop reasoning traces if any
            u = r.usage
            return Reply(text, time.time() - t0, getattr(u, "prompt_tokens", None), getattr(u, "completion_tokens", None))

        if model["provider"] == "mock":
            # Echo the first passage's label: lets tests exercise citation + scoring code paths
            labels = re.findall(r"^\[([^\]]+)\]", user, flags=re.M)
            q = user.rsplit("QUESTION:", 1)[-1]
            arabic = bool(re.search(r"[؀-ۿ]", q))
            body = "وفقاً للنص، يرجى مراجعة المادة." if arabic else "According to the passage, please see the cited rule."
            return Reply(f"{body} [{labels[0]}]" if labels else body, time.time() - t0, len(user) // 4, 20)

        raise ValueError(f"unknown provider {model['provider']}")
    except Exception as e:  # record the failure instead of crashing the whole run
        return Reply("", time.time() - t0, None, None, error=f"{type(e).__name__}: {e}")
