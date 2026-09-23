import re
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer

DOCS_DIR = Path(__file__).parent / "docs"
SIMILARITY_THRESHOLD = 0.35
TOP_K = 2

# Docs listed here are multi-topic references, not single-issue playbooks — they're
# split into one retrievable unit per `##` section instead of embedded whole.
REFERENCE_DOCS = {"company-profile"}

_model: SentenceTransformer | None = None
_units: list[dict] | None = None  # each: {"doc", "section" (None for atomic), "text"}
_embeddings: np.ndarray | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _chunk_by_heading(text: str) -> list[dict]:
    """Split a reference doc into one unit per top-level `##` section.

    Content before the first `##` (title, byline, intro) is dropped — it's framing,
    not a retrievable fact, and every KB unit here is a standalone section.
    """
    parts = re.split(r"(?m)^## ", text)
    sections = []
    for part in parts[1:]:  # parts[0] is the pre-heading preamble
        heading, _, body = part.partition("\n")
        sections.append({"section": heading.strip(), "text": f"## {heading}\n{body}".strip()})
    return sections


def _get_units() -> list[dict]:
    global _units
    if _units is None:
        units = []
        for p in sorted(DOCS_DIR.glob("*.md")):
            text = p.read_text()
            if p.stem in REFERENCE_DOCS:
                for sec in _chunk_by_heading(text):
                    units.append({"doc": p.stem, "section": sec["section"], "text": sec["text"]})
            else:
                units.append({"doc": p.stem, "section": None, "text": text})
        _units = units
    return _units


def _get_embeddings() -> np.ndarray:
    global _embeddings
    if _embeddings is None:
        texts = [u["text"] for u in _get_units()]
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


def retrieve(query: str) -> list[dict]:
    """Return up to TOP_K best-matching KB units, ranked together across all
    source docs (whole atomic docs and individual reference-doc sections alike),
    each above SIMILARITY_THRESHOLD. Empty list if nothing clears the bar.
    """
    query_vec = _get_model().encode([query], normalize_embeddings=True)[0]
    scores = np.dot(_get_embeddings(), query_vec)
    units  = _get_units()

    order = np.argsort(scores)[::-1]
    results = []
    for idx in order:
        if len(results) >= TOP_K or scores[idx] < SIMILARITY_THRESHOLD:
            break
        u = units[idx]
        results.append({
            "doc":        u["doc"],
            "section":    u["section"],
            "text":       u["text"],
            "score":      float(scores[idx]),
            "highlights": _top_lines(u["text"], query_vec),
        })
    return results
