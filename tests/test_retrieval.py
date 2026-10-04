from pathlib import Path

from app.retrieval import Index, split_document, tokenize

DOCS = Path(__file__).resolve().parent.parent / "docs"
MIN_SCORE = 4.5


def test_tokenize_drops_stopwords():
    assert tokenize("What is the price of a tap?") == ["price", "tap"]


def test_every_document_is_chunked():
    for path in DOCS.glob("*.md"):
        assert split_document(path), f"{path.name} produced no chunks"


def test_pricing_question_finds_the_pricing_document():
    index = Index(DOCS)
    hits = index.search("how much is the standard call out fee")
    assert hits
    assert hits[0][0].document == "01-services-and-pricing.md"


def test_ambiguous_fee_question_returns_both_fee_documents():
    index = Index(DOCS)
    docs = {chunk.document for chunk, _ in index.search("how much is the call out fee")}
    assert "01-services-and-pricing.md" in docs
    assert "04-emergency-callouts.md" in docs


def test_emergency_question_finds_the_emergency_document():
    index = Index(DOCS)
    hits = index.search("what does a night emergency visit cost")
    assert hits[0][0].document == "04-emergency-callouts.md"


def test_out_of_scope_questions_score_below_the_guard():
    index = Index(DOCS)
    for question in ("do you install swimming pools in Canada", "what is the weather tomorrow"):
        hits = index.search(question)
        top = hits[0][1] if hits else 0.0
        assert top < MIN_SCORE, f"{question!r} scored {top}, the guard would let it through"


def test_real_questions_score_above_the_guard():
    index = Index(DOCS)
    for question in (
        "What does an emergency call out cost at night?",
        "How long is the workmanship guarantee?",
        "Can I cancel an appointment on the day?",
        "Do you take American Express?",
    ):
        assert index.search(question)[0][1] >= MIN_SCORE
