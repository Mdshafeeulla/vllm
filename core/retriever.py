# core/retriever.py
import numpy as np
from rank_bm25 import BM25Okapi
from core.config import cfg


def hybrid_search(
    store,
    query_vec: np.ndarray,
    query_text: str,
    department: str,
    top_k: int = None,
) -> list[dict]:
    """
    Two-stage hybrid retrieval:
      1. ANN search in LanceDB (ABAC-filtered by department)
      2. BM25 re-rank on the candidates

    Fuses scores: semantic_weight * ANN + (1 - semantic_weight) * BM25
    Returns top_k results sorted by combined score.
    """
    top_k = top_k or cfg.top_k

    # Stage 1 — ANN candidates (already department-filtered)
    candidates = store.search(query_vec, department=department, top_k=top_k * 3)

    if not candidates:
        return []

    # Stage 2 — BM25 re-rank on candidate texts only (fast: small set)
    tokenized_docs = [c["text"].lower().split() for c in candidates]
    bm25 = BM25Okapi(tokenized_docs)
    bm25_scores = bm25.get_scores(query_text.lower().split())

    # Normalize BM25 scores to [0, 1]
    max_bm25 = float(max(bm25_scores)) if max(bm25_scores) > 0 else 1.0
    bm25_norm = [float(s) / max_bm25 for s in bm25_scores]

    # Fuse scores
    fused = []
    for i, candidate in enumerate(candidates):
        sem = candidate["score"]
        bm = bm25_norm[i]
        combined = cfg.semantic_weight * sem + (1 - cfg.semantic_weight) * bm
        fused.append({**candidate, "score": round(combined, 4)})

    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused[:top_k]
