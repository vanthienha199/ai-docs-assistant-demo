"""DocDesk: a document grounded assistant with verified citations.

Run:  uvicorn app:app --reload
Then: http://127.0.0.1:8000
"""

import os
import pathlib
import shutil

from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from rag.pipeline import Assistant

BASE = pathlib.Path(__file__).parent
DOCS = BASE / os.environ.get("ASSISTANT_DOCS", "documents")

app = FastAPI(title="DocDesk sample assistant")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

assistant = Assistant(DOCS)

SUGGESTED = [
    "How much is an emergency callout on a Sunday?",
    "Do you cover Maple Ridge?",
    "What is the warranty on a new water heater?",
    "What happens if I cancel 2 hours before?",
]


@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str | None = None):
    result = assistant.ask(q) if q else None
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "result": result,
            "question": q or "",
            "suggested": SUGGESTED,
            "doc_count": len(assistant.docs),
            "chunk_count": assistant.index.stats()["chunks"],
        },
    )


@app.get("/documents", response_class=HTMLResponse)
def documents(request: Request):
    return templates.TemplateResponse(
        request,
        "documents.html",
        {"docs": assistant.docs, "stats": assistant.index.stats()},
    )


@app.post("/api/ask")
def api_ask(payload: dict):
    q = (payload or {}).get("question", "").strip()
    if not q:
        return JSONResponse({"error": "question is required"}, status_code=400)
    return assistant.ask(q)


@app.post("/documents/upload")
async def upload(file: UploadFile):
    if not file.filename.endswith(".md"):
        return JSONResponse({"error": "only .md files are accepted"}, status_code=400)
    target = DOCS / pathlib.Path(file.filename).name
    with target.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    assistant.reload()
    return RedirectResponse("/documents", status_code=303)


@app.post("/documents/reindex")
def reindex():
    assistant.reload()
    return RedirectResponse("/documents", status_code=303)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "documents": len(assistant.docs), **assistant.index.stats()}
