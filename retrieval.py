from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

DOCS_DIR = Path(__file__).parent / "docs"
SIMILARITY_THRESHOLD = 0.35

_model: SentenceTransformer | None = None
_docs: dict[str, str] | None = None
_embeddings: np.ndarray | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_docs() -> dict[str, str]:
    global _docs
    if _docs is None:
        _docs = {p.stem: p.read_text() for p in sorted(DOCS_DIR.glob("*.md"))}
    return _docs


def _get_embeddings() -> np.ndarray:
    global _embeddings
    if _embeddings is None:
        texts = list(_get_docs().values())
        _embeddings = _get_model().encode(texts, normalize_embeddings=True)
    return _embeddings


def _top_lines(doc_text: str, query_vec: np.ndarray, n: int = 3) -> list[dict]:
    """Return up to n lines from doc_text most similar to query_vec.

    Reuses the already-loaded model — no extra model download or init.
    Lines shorter than 25 chars (headers, blank rows) are skipped.
    Lines scoring below 0.25 are suppressed even if they're top-n.
    """
    lines = [l.strip() for l in doc_text.split("\n") if len(l.strip()) >= 25]
    if not lines:
        return []
    vecs   = _get_model().encode(lines, normalize_embeddings=True)
    scores = np.dot(vecs, query_vec)
    top_n  = min(n, len(lines))
    top_idx = np.argsort(scores)[::-1][:top_n]
    return [
        {"text": lines[i], "score": float(scores[i])}
        for i in top_idx
        if scores[i] >= 0.25
    ]


def retrieve(query: str) -> dict | None:
    """Return the best-matching KB article, or None if below threshold."""
    query_vec = _get_model().encode([query], normalize_embeddings=True)[0]
    scores    = np.dot(_get_embeddings(), query_vec)
    idx       = int(np.argmax(scores))
    score     = float(scores[idx])
    if score < SIMILARITY_THRESHOLD:
        return None
    docs  = _get_docs()
    names = list(docs.keys())
    texts = list(docs.values())
    return {
        "name":       names[idx],
        "content":    texts[idx],
        "score":      score,
        "highlights": _top_lines(texts[idx], query_vec),
    }
