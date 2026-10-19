import numpy as np

from core.config import cfg
from core.store import VectorStore


def test_deleted_document_can_be_restored(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "db_path", str(tmp_path))
    monkeypatch.setattr(cfg, "table_name", "recycle_test")
    vector_store = VectorStore()

    vector_store.add_documents(
        [{"text": "VPN support", "chunk_idx": 0}],
        np.zeros((1, cfg.embed_dimensions), dtype=np.float32),
        "it",
        "guide.pdf",
    )

    vector_store.delete_source("it", "guide.pdf")
    assert vector_store.list_sources("it") == []
    entries = vector_store.list_recycle_bin()
    assert len(entries) == 1
    assert entries[0]["source"] == "guide.pdf"

    vector_store.restore_source(entries[0]["deletion_id"])

    assert vector_store.list_sources("it") == ["guide.pdf"]
    assert vector_store.list_recycle_bin() == []
