from pathlib import Path

from app.handbook import to_html
from app.retrieval import Index

DOCS = Path(__file__).resolve().parent.parent / "docs"


def test_price_table_becomes_a_table_with_right_aligned_figures():
    index = Index(DOCS)
    chunk = next(c for c in index.chunks if c.heading == "Fixed price jobs")
    html = to_html(chunk.text)
    assert "<table>" in html
    assert html.count("<tr>") == 6, "a header row and five jobs"
    assert '<td class="num">240 dollars</td>' in html
    assert "---" not in html, "the markdown separator row is not content"


def test_bullet_list_becomes_a_list():
    index = Index(DOCS)
    chunk = next(c for c in index.chunks if c.heading == "Appointment windows")
    html = to_html(chunk.text)
    assert "<ul>" in html and html.count("<li>") == 3
    assert "- Morning" not in html


def test_markup_in_a_passage_is_escaped():
    assert to_html("Price is <b>89</b> dollars") == "<p>Price is &lt;b&gt;89&lt;/b&gt; dollars</p>"


def test_every_passage_renders_to_something():
    index = Index(DOCS)
    for chunk in index.chunks:
        assert to_html(chunk.text).startswith("<")
