"""Answer generation with pluggable backends.

anthropic_api  calls the Anthropic Messages API with ANTHROPIC_API_KEY
claude_cli     shells out to a local Claude Code CLI, useful when no API credit is available
extractive     no model at all, returns the best matching passage, so the demo always runs

Every backend receives the same grounded prompt and must answer only from the
retrieved passages, citing them as [1], [2] and so on.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request

SYSTEM = (
    "You are a support assistant for Blue Harbor Plumbing, a sample company. "
    "Answer only from the numbered passages supplied by the user. "
    "Cite every fact with the matching number in square brackets, like [1]. "
    "If the passages do not contain the answer, reply exactly: "
    "I could not find that in the Blue Harbor documents. "
    "Never invent prices, timeframes or policies. "
    "Write two to four short sentences in plain English. Do not use dashes as punctuation."
)


def build_prompt(question: str, passages: list[dict]) -> str:
    blocks = []
    for item in passages:
        blocks.append(f"[{item['n']}] Source: {item['label']}\n{item['text']}")
    joined = "\n\n".join(blocks)
    return f"Passages:\n\n{joined}\n\nQuestion: {question}\n\nAnswer using only the passages above."


def _anthropic_api(question: str, passages: list[dict], model: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    payload = {
        "model": model,
        "max_tokens": 400,
        "system": SYSTEM,
        "messages": [{"role": "user", "content": build_prompt(question, passages)}],
    }
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.load(response)
    return body["content"][0]["text"].strip()


def _claude_cli(question: str, passages: list[dict], model: str) -> str:
    environment = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    prompt = f"{SYSTEM}\n\n{build_prompt(question, passages)}"
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", model],
        capture_output=True,
        text=True,
        timeout=180,
        env=environment,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[:200] or "claude cli failed")
    return result.stdout.strip()


def _extractive(question: str, passages: list[dict], model: str) -> str:
    best = passages[0]
    first = best["text"].split("\n")[0].strip()
    return f"{first} [1]"


MODEL = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")

BACKENDS = {
    "anthropic_api": _anthropic_api,
    "claude_cli": _claude_cli,
    "extractive": _extractive,
}


def answer(question: str, passages: list[dict]) -> tuple[str, str]:
    """Return (answer_text, backend_actually_used)."""
    name = os.environ.get("LLM_BACKEND", "anthropic_api")
    model = MODEL
    order = [name] + [b for b in ("claude_cli", "extractive") if b != name]
    last_error = ""
    for backend in order:
        try:
            return BACKENDS[backend](question, passages, model), backend
        except Exception as error:  # fall through to the next backend
            last_error = f"{backend}: {error}"
    return f"The assistant could not reach a model backend. {last_error}", "none"
