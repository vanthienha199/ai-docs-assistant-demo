"""FastAPI app: a support assistant that answers only from a folder of documents."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .handbook import to_html
from .llm import MODEL, answer as generate_answer
from .retrieval import Index

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = Path(os.environ.get("DOCS_DIR", ROOT / "docs"))
STATIC_DIR = ROOT / "static"
MIN_SCORE = float(os.environ.get("MIN_SCORE", "4.5"))
MIN_COVERAGE = float(os.environ.get("MIN_COVERAGE", "0.34"))
NO_ANSWER = "That is not covered in the Blue Harbor handbook."

app = FastAPI(title="Blue Harbor Support Assistant (Sample)")
index = Index(DOCS_DIR)


class Question(BaseModel):
    question: str


def snippet_of(text: str, limit: int = 260) -> str:
    """Flatten a passage for display. Markdown table pipes are turned into
    readable separators so a price table does not show up as a row of dashes."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.fullmatch(r"\|[\s|:-]*\|", stripped):
            continue  # a table separator row carries no information
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|") if c.strip()]
            stripped = " · ".join(cells)
        lines.append(stripped)
    flat = re.sub(r"\s+", " ", " ".join(lines)).strip()
    return flat if len(flat) <= limit else flat[:limit].rsplit(" ", 1)[0] + "..."


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/admin")
def admin() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/api/handbook")
def handbook() -> dict:
    """The whole handbook as printed pages, so the source pane can scroll to any
    citation without a second round trip."""
    return {
        "pages": [
            {
                "page": page["page"],
                "title": page["title"],
                "document": page["document"],
                "blocks": [
                    {
                        "anchor": block["anchor"],
                        "heading": block["heading"],
                        "html": to_html(block["text"]),
                    }
                    for block in page["blocks"]
                ],
            }
            for page in index.pages
        ],
        "documents": [
            {"title": d["title"], "filename": d["filename"]} for d in index.documents
        ],
    }


@app.get("/api/documents")
def list_documents() -> dict:
    return {
        "documents": index.documents,
        "total_chunks": len(index.chunks),
        "docs_dir": DOCS_DIR.name,
    }


@app.post("/api/reindex")
def reindex() -> dict:
    started = time.perf_counter()
    index.build()
    return {
        "ok": True,
        "chunks": len(index.chunks),
        "ms": round((time.perf_counter() - started) * 1000, 1),
    }


@app.post("/api/documents")
async def upload(file: UploadFile) -> dict:
    name = Path(file.filename or "").name
    if Path(name).suffix.lower() not in {".md", ".txt", ".markdown"}:
        raise HTTPException(status_code=400, detail="Only .md, .markdown and .txt files are accepted")
    payload = await file.read()
    if len(payload) > 2_000_000:
        raise HTTPException(status_code=400, detail="File is larger than 2 MB")
    (DOCS_DIR / name).write_bytes(payload)
    index.build()
    return {"ok": True, "filename": name, "chunks": len(index.chunks)}


@app.post("/api/chat")
def chat(payload: Question) -> JSONResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Ask a question first")

    started = time.perf_counter()
    hits = index.search(question, top_k=4)
    coverage = index.vocabulary_coverage(question)
    # Two signals have to agree before the model is allowed to answer: the best
    # passage has to score well, and the question has to be made of words this
    # corpus actually knows. Either one alone lets odd questions through.
    grounded = bool(hits) and hits[0][1] >= MIN_SCORE and coverage >= MIN_COVERAGE

    if not grounded:
        return JSONResponse(
            {
                "answer": NO_ANSWER
                + " The five documents cover pricing, booking, warranty, emergency call outs and payment.",
                "grounded": False,
                "status": "not_in_handbook",
                "citations": [],
                "backend": "guard",
                "model": "retrieval guard, no model call",
                "top_score": hits[0][1] if hits else 0.0,
                "coverage": coverage,
                "ms": round((time.perf_counter() - started) * 1000, 1),
            }
        )

    passages = [
        {
            "n": i + 1,
            "label": chunk.label,
            "document": chunk.document,
            "heading": chunk.heading,
            "page": chunk.page,
            "anchor": chunk.anchor,
            "cite": chunk.cite,
            "text": chunk.text,
            "snippet": snippet_of(chunk.text),
            "score": score,
        }
        for i, (chunk, score) in enumerate(hits)
    ]
    text, backend = generate_answer(question, passages)

    # Verify citations against what was actually retrieved. A model can invent a
    # number like [7] when only four passages exist. Those markers are removed
    # before the answer reaches the page, and the count is reported.
    cited = [int(n) for n in re.findall(r"\[(\d+)\]", text)]
    valid = sorted({n for n in cited if 1 <= n <= len(passages)})
    dropped = len([n for n in cited if not 1 <= n <= len(passages)])
    text = re.sub(
        r"\s*\[(\d+)\]",
        lambda mo: mo.group(0) if 1 <= int(mo.group(1)) <= len(passages) else "",
        text,
    )
    citations = [p for p in passages if p["n"] in valid] or passages[:1]

    return JSONResponse(
        {
            "answer": text,
            "grounded": True,
            "status": "answered",
            "citations": [
                {k: v for k, v in c.items() if k != "text"} for c in citations
            ],
            "backend": backend,
            "model": MODEL,
            "top_score": hits[0][1],
            "coverage": coverage,
            "dropped_citations": dropped,
            "ms": round((time.perf_counter() - started) * 1000, 1),
        }
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
