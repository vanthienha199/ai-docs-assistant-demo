"""Pluggable answer generation. Three backends, selected by ASSISTANT_BACKEND."""

import json
import os
import re
import subprocess
import urllib.request

SYSTEM = (
    "You answer questions using only the numbered context passages supplied.\n"
    "Rules you must follow:\n"
    "1. Cite every factual sentence with a bracketed passage number, for example [2].\n"
    "2. Never state a fact that is not in a passage. Do not use outside knowledge.\n"
    "3. If the passages do not answer the question, reply with exactly: "
    "NOT_IN_DOCUMENTS\n"
    "4. Keep the answer under 90 words. Be direct and plain.\n"
    "5. Do not use em dashes."
)


def _prompt(question, passages):
    blocks = []
    for i, p in enumerate(passages, 1):
        blocks.append(f"[{i}] Source: {p['chunk'].citation_label}\n{p['chunk'].text}")
    return f"{SYSTEM}\n\nContext passages:\n\n" + "\n\n".join(blocks) + f"\n\nQuestion: {question}\nAnswer:"


def _anthropic(question, passages, model):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    body = json.dumps(
        {
            "model": model,
            "max_tokens": 400,
            "messages": [{"role": "user", "content": _prompt(question, passages)}],
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["content"][0]["text"].strip()


def _claude_cli(question, passages, model):
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    proc = subprocess.run(
        ["claude", "-p", _prompt(question, passages), "--model", model],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude cli failed: {proc.stderr[:200]}")
    return proc.stdout.strip()


def _extractive(question, passages, model):
    """No API key needed. Quotes the best passage and cites it."""
    if not passages:
        return "NOT_IN_DOCUMENTS"
    best = passages[0]["chunk"].text
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", best) if s.strip()]
    return " ".join(sentences[:3]) + " [1]"


BACKENDS = {"anthropic": _anthropic, "claude_cli": _claude_cli, "extractive": _extractive}


def generate(question, passages):
    name = os.environ.get("ASSISTANT_BACKEND", "extractive")
    model = os.environ.get("ASSISTANT_MODEL", "claude-haiku-4-5-20251001")
    fn = BACKENDS.get(name)
    if not fn:
        raise RuntimeError(f"unknown backend {name}, pick one of {sorted(BACKENDS)}")
    return fn(question, passages, model), name
