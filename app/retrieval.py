"""Heading aware chunking and BM25 retrieval over a folder of markdown or text files.

No external search service and no vector database. Everything runs locally so the
demo starts with one command and no account to create.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

WORD = re.compile(r"[a-z0-9]+")

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from",
    "how", "i", "if", "in", "is", "it", "its", "me", "my", "of", "on", "or", "that", "the",
    "then", "there", "they", "this", "to", "was", "we", "what", "when", "where", "which",
    "who", "will", "with", "you", "your",
}

SYNONYMS = {
    "cost": ["price", "fee", "charge", "rate"],
    "price": ["cost", "fee", "charge", "rate"],
    "fee": ["cost", "price", "charge"],
    "cancel": ["cancellation", "reschedule"],
    "refund": ["return", "credit"],
    "guarantee": ["warranty", "guaranteed"],
    "warranty": ["guarantee", "guaranteed"],
    "urgent": ["emergency"],
    "emergency": ["urgent", "burst", "flooding"],
    "weekend": ["saturday", "sunday"],
    "pay": ["payment", "invoice", "card"],
    "book": ["booking", "appointment", "schedule"],
    "late": ["delay", "delayed", "overdue"],
}


def tokenize(text: str) -> list[str]:
    return [t for t in WORD.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


def expand(tokens: list[str]) -> list[str]:
    out = list(tokens)
    for t in tokens:
        out.extend(SYNONYMS.get(t, []))
    return out


@dataclass
class Chunk:
    chunk_id: int
    document: str
    title: str
    heading: str
    text: str
    tokens: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.title} > {self.heading}" if self.heading else self.title


def _title_of(path: Path, body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def split_document(path: Path, max_chars: int = 900) -> list[tuple[str, str, str]]:
    """Return (title, heading, text) tuples, split on markdown headings then by size."""
    body = path.read_text(encoding="utf-8", errors="ignore")
    title = _title_of(path, body)

    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in body.splitlines():
        if re.match(r"^#{2,4}\s+", line):
            sections.append((re.sub(r"^#{2,4}\s+", "", line).strip(), []))
        elif line.startswith("# "):
            continue
        else:
            sections[-1][1].append(line)

    out: list[tuple[str, str, str]] = []
    for heading, lines in sections:
        text = "\n".join(lines).strip()
        if not text:
            continue
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        buffer = ""
        for para in paragraphs:
            if buffer and len(buffer) + len(para) + 2 > max_chars:
                out.append((title, heading, buffer.strip()))
                buffer = para
            else:
                buffer = f"{buffer}\n\n{para}" if buffer else para
        if buffer.strip():
            out.append((title, heading, buffer.strip()))
    return out


class Index:
    """BM25 index built in memory from a folder of documents."""

    K1 = 1.4
    B = 0.75

    def __init__(self, docs_dir: Path):
        self.docs_dir = Path(docs_dir)
        self.chunks: list[Chunk] = []
        self.doc_freq: dict[str, int] = {}
        self.avg_len: float = 0.0
        self.build()

    @property
    def documents(self) -> list[dict]:
        seen: dict[str, dict] = {}
        for path in sorted(self.docs_dir.glob("*")):
            if path.suffix.lower() not in {".md", ".txt", ".markdown"}:
                continue
            chunks = [c for c in self.chunks if c.document == path.name]
            seen[path.name] = {
                "filename": path.name,
                "title": chunks[0].title if chunks else path.stem,
                "chunks": len(chunks),
                "words": sum(len(c.text.split()) for c in chunks),
                "bytes": path.stat().st_size,
            }
        return list(seen.values())

    def build(self) -> None:
        self.chunks = []
        chunk_id = 0
        for path in sorted(self.docs_dir.glob("*")):
            if path.suffix.lower() not in {".md", ".txt", ".markdown"}:
                continue
            for title, heading, text in split_document(path):
                # Headings describe what a passage is about, so they are weighted
                # more heavily than body text. This is ordinary field boosting.
                tokens = tokenize(text) + tokenize(heading) * 3 + tokenize(title) * 2
                self.chunks.append(Chunk(chunk_id, path.name, title, heading, text, tokens))
                chunk_id += 1

        self.doc_freq = {}
        for chunk in self.chunks:
            for term in set(chunk.tokens):
                self.doc_freq[term] = self.doc_freq.get(term, 0) + 1
        lengths = [len(c.tokens) for c in self.chunks] or [1]
        self.avg_len = sum(lengths) / len(lengths)

    def _idf(self, term: str) -> float:
        n = len(self.chunks)
        df = self.doc_freq.get(term, 0)
        if df == 0:
            return 0.0
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(self, question: str, top_k: int = 4) -> list[tuple[Chunk, float]]:
        query = expand(tokenize(question))
        if not query:
            return []
        scored: list[tuple[Chunk, float]] = []
        for chunk in self.chunks:
            counts: dict[str, int] = {}
            for term in chunk.tokens:
                counts[term] = counts.get(term, 0) + 1
            length = len(chunk.tokens) or 1
            score = 0.0
            for term in query:
                tf = counts.get(term, 0)
                if not tf:
                    continue
                denom = tf + self.K1 * (1 - self.B + self.B * length / self.avg_len)
                score += self._idf(term) * (tf * (self.K1 + 1)) / denom
            if score > 0:
                scored.append((chunk, round(score, 3)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]
