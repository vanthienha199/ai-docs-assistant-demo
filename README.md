# Document assistant with citations (sample project)

A small support assistant that answers questions **only** from a folder of your own documents, cites the exact passage behind every sentence, and refuses to answer when the documents do not cover the question. The sample content is a fictional plumbing company called Blue Harbor, written for this demo.

Retrieval is heading aware chunking plus BM25 ranking in plain Python, so there is no vector database to host and no search service to pay for. Answer writing is pluggable: the Anthropic API, a local Claude CLI, or a no model extractive mode so the app still runs with no key at all.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your ANTHROPIC_API_KEY
python3 -m uvicorn app.main:app --port 8000
```

Open http://127.0.0.1:8000 for the assistant and http://127.0.0.1:8000/admin to see the indexed documents or upload a new one. Run the tests with `python3 -m pytest tests -q`.

## Swap in your own documents

Drop `.md` or `.txt` files into `docs/` and restart, or upload them on the admin page. Change the company name in `app/llm.py` and the wording in `static/index.html`, and the assistant is yours.

| Setting | What it does |
| --- | --- |
| `LLM_BACKEND` | `anthropic_api`, `claude_cli` or `extractive` |
| `LLM_MODEL` | Model name passed to the backend |
| `DOCS_DIR` | Folder the assistant is allowed to read |
| `MIN_SCORE` | Retrieval score needed before the assistant may answer at all |

Built by Ha Le as a portfolio sample. No client data is used anywhere in this repository.

## Two things that are not in a basic RAG demo

**The refusal is real logic.** Retrieval runs first and two signals have to agree before
the model is called: the best passage must score above `MIN_SCORE`, and the question must
be made of words the corpus actually knows (`MIN_COVERAGE`). Either signal alone lets odd
questions through. An out of scope question therefore returns in about 2 ms and reports
`retrieval guard, no model call`.

**Citations are verified after generation.** A model can write `[7]` when only four
passages were retrieved. Every marker is checked against what was really retrieved,
invalid ones are stripped before the answer reaches the page, and the count is returned
as `dropped_citations`.

## Themes

The UI ships dark and light. Append `?theme=light` to any page to switch.
