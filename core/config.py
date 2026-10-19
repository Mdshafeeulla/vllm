# core/config.py
import os
from dataclasses import dataclass, field


@dataclass
class Config:
    # ── Paths ────────────────────────────────────────────────────────
    db_path: str = "data/lancedb"
    table_name: str = "enterprise_docs"

    # ── Embedder ─────────────────────────────────────────────────────
    embed_model: str = "nomic-ai/nomic-embed-text-v1.5"
    embed_device: str = os.getenv("EMBED_DEVICE", "auto")
    embed_dimensions: int = 256         # MRL: 256 of 768 dims

    # ── Chunking ─────────────────────────────────────────────────────
    chunk_size: int = 300               # words per chunk
    chunk_overlap: int = 50             # words overlap between chunks

    # ── Retrieval ────────────────────────────────────────────────────
    top_k: int = 4                       # 4 chunks is optimal for speed & context accuracy
    semantic_weight: float = 0.65       # 0.65 ANN + 0.35 BM25

    # ── LLM ──────────────────────────────────────────────────────────
    ollama_model: str = "llama3.2:1b"
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "8192"))

    # ── Departments ───────────────────────────────────────────────────
    default_department: str = "it"
    department_display_name: str = "IT Support"
    departments: list = field(default_factory=lambda: [
        "it",
    ])

    # ── Available LLMs (must be pulled via `ollama pull`) ────────────
    available_models: list = field(default_factory=lambda: [
        "mistral",
        "llama3.2:1b",
    ])


cfg = Config()  # singleton — import this everywhere
