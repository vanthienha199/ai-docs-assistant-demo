"""Split markdown documents into chunks that remember their heading path."""

import re
from dataclasses import dataclass, field

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
TARGET_WORDS = 170
MAX_WORDS = 260


@dataclass
class Chunk:
    doc_id: str
    doc_title: str
    section: str
    text: str
    ordinal: int
    tokens: list = field(default_factory=list)

    @property
    def citation_label(self):
        if self.section:
            return f"{self.doc_title} > {self.section}"
        return self.doc_title


def _flush(buf, doc_id, doc_title, section, out):
    body = "\n".join(buf).strip()
    if not body:
        return
    out.append(
        Chunk(
            doc_id=doc_id,
            doc_title=doc_title,
            section=section,
            text=body,
            ordinal=len(out),
        )
    )


def chunk_markdown(doc_id, raw):
    """Return a list of Chunk. Headings start a new chunk; long sections split on blank lines."""
    lines = raw.splitlines()
    doc_title = doc_id
    section = ""
    buf = []
    out = []

    for line in lines:
        m = HEADING.match(line)
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            _flush(buf, doc_id, doc_title, section, out)
            buf = []
            if level == 1:
                doc_title = title
                section = ""
            else:
                section = title
            continue

        buf.append(line)
        if len(" ".join(buf).split()) >= MAX_WORDS and not line.strip():
            _flush(buf, doc_id, doc_title, section, out)
            buf = []

    _flush(buf, doc_id, doc_title, section, out)

    merged = []
    for c in out:
        if (
            merged
            and merged[-1].section == c.section
            and len(merged[-1].text.split()) + len(c.text.split()) < TARGET_WORDS
        ):
            merged[-1].text = merged[-1].text + "\n" + c.text
            continue
        c.ordinal = len(merged)
        merged.append(c)
    return merged
