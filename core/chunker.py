# core/chunker.py
from core.config import cfg


def chunk_text(text: str) -> list[dict]:
    """
    Split text into overlapping word-based chunks.
    Returns list of dicts: {"text": str, "chunk_idx": int}
    """
    if not text or not text.strip():
        return []

    words = text.split()
    step = max(1, cfg.chunk_size - cfg.chunk_overlap)
    chunks = []
    idx = 0

    for start in range(0, len(words), step):
        chunk_words = words[start : start + cfg.chunk_size]
        if len(chunk_words) < 10:  # skip tiny trailing pieces
            continue
        chunks.append({"text": " ".join(chunk_words), "chunk_idx": idx})
        idx += 1

    return chunks
