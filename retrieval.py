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


def retrieve(query: str) -> dict | None:
    """Return the best-matching KB article, or None if below threshold."""
    query_vec = _get_model().encode([query], normalize_embeddings=True)[0]
    scores = np.dot(_get_embeddings(), query_vec)
    idx = int(np.argmax(scores))
    score = float(scores[idx])
    if score < SIMILARITY_THRESHOLD:
        return None
    docs = _get_docs()
    names, texts = list(docs.keys()), list(docs.values())
    return {"name": names[idx], "content": texts[idx], "score": score}
