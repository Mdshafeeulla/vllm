# core/embedder.py
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from core.config import cfg
from utils.logger import log

_model = None


def _resolve_device() -> str:
    configured_device = cfg.embed_device.lower()
    if configured_device == "cpu":
        return "cpu"

    cuda_available = torch.cuda.is_available()

    if configured_device == "auto":
        return "cuda" if cuda_available else "cpu"
    if configured_device.startswith("cuda") and not cuda_available:
        log.warning("CUDA is unavailable; using CPU for embeddings.")
        return "cpu"
    return cfg.embed_device


def _get_model():
    global _model
    if _model is None:
        device = _resolve_device()
        log.info(f"[Embedder] Loading '{cfg.embed_model}' on device='{device}'...")
        _model = SentenceTransformer(
            cfg.embed_model,
            device=device,
            trust_remote_code=True,  # required for nomic-embed-text-v1.5
            prompts={"query": "search_query: ", "document": "search_document: "},
        )
        log.info("[Embedder] Model ready ✓")
    return _model


def embed_texts(texts: list[str], batch_size: int = 16, progress_callback=None) -> np.ndarray:
    """
    Embed a batch of document texts with controlled batching to prevent CPU overload.
    Uses nomic 'search_document' prompt for better retrieval accuracy.
    Returns float32 array of shape (N, cfg.embed_dimensions).

    Args:
        texts: list of text strings to embed
        batch_size: number of texts to embed per batch (lower = less CPU spike)
        progress_callback: optional callable(batch_num, total_batches) for progress
    """
    if isinstance(texts, str):
        texts = [texts]

    model = _get_model()
    total_batches = (len(texts) + batch_size - 1) // batch_size
    all_vecs = []

    for batch_idx in range(0, len(texts), batch_size):
        batch = texts[batch_idx : batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1

        vecs = model.encode(
            batch,
            prompt_name="document",
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=len(batch),  # process entire mini-batch at once
        )
        # MRL truncation: use only first `embed_dimensions` dims
        all_vecs.append(vecs[:, : cfg.embed_dimensions].astype("float32"))

        if progress_callback:
            try:
                progress_callback(batch_num, total_batches)
            except Exception:
                pass

    return np.concatenate(all_vecs, axis=0)


def embed_query(text: str) -> np.ndarray:
    """
    Embed a single user query.
    Uses nomic 'search_query' prompt (asymmetric encoding = better recall).
    Returns 1D float32 array of shape (cfg.embed_dimensions,).
    """
    vec = _get_model().encode(
        [text],
        prompt_name="query",
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vec[0, : cfg.embed_dimensions].astype("float32")
