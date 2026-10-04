"""Retrieve, gate on grounding, generate, then verify every citation."""

import html
import pathlib
import re

from .chunker import chunk_markdown
from .index import Bm25Index
from .llm import generate

CITE = re.compile(r"\[(\d+)\]")


def to_html(answer, valid_max):
    """Escape the answer and turn valid [n] markers into superscript chips."""
    out = html.escape(answer)
    return re.sub(
        r"\[(\d+)\]",
        lambda m: f"<sup>{m.group(1)}</sup>" if 1 <= int(m.group(1)) <= valid_max else "",
        out,
    )

MIN_SCORE = 2.0
MIN_COVERAGE = 0.34
REFUSAL = (
    "I could not find that in the documents I have been given. "
    "I only answer from the indexed files, so I would rather say I do not know "
    "than guess."
)


class Assistant:
    def __init__(self, doc_dir="documents"):
        self.doc_dir = pathlib.Path(doc_dir)
        self.index = Bm25Index()
        self.docs = []
        self._cache = {}
        self.reload()

    def reload(self):
        self.index = Bm25Index()
        self.docs = []
        self._cache = {}
        for path in sorted(self.doc_dir.glob("*.md")):
            raw = path.read_text()
            chunks = chunk_markdown(path.name, raw)
            self.index.add(chunks)
            self.docs.append(
                {
                    "doc_id": path.name,
                    "title": chunks[0].doc_title if chunks else path.stem,
                    "words": len(raw.split()),
                    "chunks": len(chunks),
                    "bytes": path.stat().st_size,
                }
            )
        return self.index.stats()

    def ask(self, question):
        key = question.strip().lower()
        if key in self._cache:
            return self._cache[key]
        answer = self._answer(question)
        if len(self._cache) < 256:
            self._cache[key] = answer
        return answer

    def _answer(self, question):
        hits = self.index.search(question, top_k=4)
        grounded = bool(hits) and hits[0]["score"] >= MIN_SCORE and hits[0]["coverage"] >= MIN_COVERAGE

        if not grounded:
            return {
                "question": question,
                "answer": REFUSAL,
                "answer_html": html.escape(REFUSAL),
                "grounded": False,
                "backend": "gate",
                "citations": [],
                "considered": [
                    {"label": h["chunk"].citation_label, "score": h["score"]} for h in hits[:3]
                ],
                "top_score": hits[0]["score"] if hits else 0.0,
            }

        raw, backend = generate(question, hits)

        if "NOT_IN_DOCUMENTS" in raw:
            return {
                "question": question,
                "answer": REFUSAL,
                "answer_html": html.escape(REFUSAL),
                "grounded": False,
                "backend": backend,
                "citations": [],
                "considered": [
                    {"label": h["chunk"].citation_label, "score": h["score"]} for h in hits[:3]
                ],
                "top_score": hits[0]["score"],
            }

        used, citations = [], []
        for n in CITE.findall(raw):
            i = int(n)
            if 1 <= i <= len(hits) and i not in used:
                used.append(i)
        dropped = len([n for n in CITE.findall(raw) if not (1 <= int(n) <= len(hits))])
        answer = CITE.sub(lambda m: m.group(0) if 1 <= int(m.group(1)) <= len(hits) else "", raw)

        for i in used:
            c = hits[i - 1]["chunk"]
            citations.append(
                {
                    "n": i,
                    "label": c.citation_label,
                    "doc_id": c.doc_id,
                    "snippet": c.text[:320].strip(),
                    "score": hits[i - 1]["score"],
                }
            )

        return {
            "question": question,
            "answer": answer.strip(),
            "answer_html": to_html(answer.strip(), len(hits)),
            "grounded": True,
            "backend": backend,
            "citations": citations,
            "dropped_citations": dropped,
            "considered": [
                {"label": h["chunk"].citation_label, "score": h["score"]} for h in hits
            ],
            "top_score": hits[0]["score"],
        }
