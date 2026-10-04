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

from .llm import MODEL, answer as generate_answer
from .retrieval import Index

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = Path(os.environ.get("DOCS_DIR", ROOT / "docs"))
STATIC_DIR = ROOT / "static"
MIN_SCORE = float(os.environ.get("MIN_SCORE", "4.5"))
NO_ANSWER = "I could not find that in the Blue Harbor documents."

app = FastAPI(title="Blue Harbor Support Assistant (Sample)")
index = Index(DOCS_DIR)


class Question(BaseModel):
    question: str


def snippet_of(text: str, limit: int = 260) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    return flat if len(flat) <= limit else flat[:limit].rsplit(" ", 1)[0] + "..."


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/admin")
def admin() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


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
    grounded = bool(hits) and hits[0][1] >= MIN_SCORE

    if not grounded:
        return JSONResponse(
            {
                "answer": NO_ANSWER
                + " Try asking about pricing, booking, warranty, emergency call outs or payment.",
                "grounded": False,
                "citations": [],
                "backend": "guard",
                "model": "retrieval guard, no model call",
                "top_score": hits[0][1] if hits else 0.0,
                "ms": round((time.perf_counter() - started) * 1000, 1),
            }
        )

    passages = [
        {
            "n": i + 1,
            "label": chunk.label,
            "document": chunk.document,
            "text": chunk.text,
            "snippet": snippet_of(chunk.text),
            "score": score,
        }
        for i, (chunk, score) in enumerate(hits)
    ]
    text, backend = generate_answer(question, passages)
    used = sorted({int(n) for n in re.findall(r"\[(\d+)\]", text)})
    citations = [p for p in passages if p["n"] in used] or passages[:1]

    return JSONResponse(
        {
            "answer": text,
            "grounded": True,
            "citations": [
                {k: v for k, v in c.items() if k != "text"} for c in citations
            ],
            "backend": backend,
            "model": MODEL,
            "top_score": hits[0][1],
            "ms": round((time.perf_counter() - started) * 1000, 1),
        }
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
