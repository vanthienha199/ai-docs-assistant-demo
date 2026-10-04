"""BM25 retrieval over chunks, with no third party dependencies."""

import math
import re
from collections import Counter

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "do", "does", "for",
    "from", "has", "have", "how", "i", "if", "in", "is", "it", "its", "me", "my",
    "of", "on", "or", "that", "the", "their", "them", "there", "they", "this",
    "to", "was", "we", "what", "when", "where", "which", "who", "will", "with",
    "you", "your", "can", "could", "would", "should", "much", "many", "about",
}

WORD = re.compile(r"[a-z0-9]+")
K1 = 1.5
B = 0.75


def tokenize(text):
    return [w for w in WORD.findall(text.lower()) if w not in STOPWORDS and len(w) > 1]


class Bm25Index:
    def __init__(self):
        self.chunks = []
        self.df = Counter()
        self.avg_len = 0.0

    def add(self, chunks):
        for c in chunks:
            c.tokens = tokenize(f"{c.doc_title} {c.section} {c.text}")
            self.chunks.append(c)
        self._rebuild_stats()

    def _rebuild_stats(self):
        self.df = Counter()
        for c in self.chunks:
            for t in set(c.tokens):
                self.df[t] += 1
        lengths = [len(c.tokens) for c in self.chunks] or [1]
        self.avg_len = sum(lengths) / len(lengths)

    def _idf(self, term):
        n = len(self.chunks)
        d = self.df.get(term, 0)
        if d == 0:
            return 0.0
        return math.log(1 + (n - d + 0.5) / (d + 0.5))

    def search(self, query, top_k=4):
        q = tokenize(query)
        if not q or not self.chunks:
            return []
        scored = []
        for c in self.chunks:
            tf = Counter(c.tokens)
            dl = len(c.tokens) or 1
            score = 0.0
            for term in q:
                f = tf.get(term, 0)
                if not f:
                    continue
                num = f * (K1 + 1)
                den = f + K1 * (1 - B + B * dl / self.avg_len)
                score += self._idf(term) * num / den
            if score > 0:
                scored.append((score, c))
        scored.sort(key=lambda p: p[0], reverse=True)

        hits = scored[:top_k]
        if not hits:
            return []
        best = hits[0][0]
        matched = len({t for t in q if self.df.get(t)})
        coverage = matched / len(set(q))
        return [
            {
                "chunk": c,
                "score": round(s, 3),
                "relative": round(s / best, 3),
                "coverage": round(coverage, 3),
            }
            for s, c in hits
        ]

    def stats(self):
        per_doc = Counter(c.doc_id for c in self.chunks)
        return {
            "chunks": len(self.chunks),
            "vocabulary": len(self.df),
            "avg_chunk_tokens": round(self.avg_len, 1),
            "per_doc": dict(per_doc),
        }
