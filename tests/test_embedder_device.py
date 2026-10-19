from core import embedder


def test_auto_device_uses_cpu_when_cuda_is_unavailable(monkeypatch):
    monkeypatch.setattr(embedder.cfg, "embed_device", "auto")
    monkeypatch.setattr(embedder.torch.cuda, "is_available", lambda: False)

    assert embedder._resolve_device() == "cpu"


def test_auto_device_uses_cuda_when_available(monkeypatch):
    monkeypatch.setattr(embedder.cfg, "embed_device", "auto")
    monkeypatch.setattr(embedder.torch.cuda, "is_available", lambda: True)

    assert embedder._resolve_device() == "cuda"