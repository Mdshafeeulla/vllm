import pytest

from core import monitoring


def test_format_bytes_uses_binary_units():
    assert monitoring.format_bytes(1024) == "1.0 KB"
    assert monitoring.format_bytes(1024**3) == "1.0 GB"


def test_resource_snapshot_reports_cpu_memory_and_storage():
    snapshot = monitoring.resource_snapshot()

    assert snapshot["cpu_cores"] > 0
    assert snapshot["cpu_cores_available"] > 0
    assert snapshot["memory_total_bytes"] > 0
    assert snapshot["memory_available_bytes"] >= 0
    assert snapshot["disk_total_bytes"] > 0
    assert snapshot["disk_free_bytes"] >= 0


@pytest.mark.parametrize(
    "error",
    [
        MemoryError("allocation failed"),
        RuntimeError("CUDA out of memory"),
        RuntimeError("cannot allocate memory"),
    ],
)
def test_detects_memory_exhaustion(error):
    assert monitoring.is_out_of_memory_error(error)


def test_indexing_status_records_oom(monkeypatch):
    monkeypatch.setattr(monitoring, "resource_snapshot", lambda: {})

    with pytest.raises(MemoryError):
        with monitoring.track_indexing("guide.pdf") as report_progress:
            report_progress("embedding", 1, 2)
            raise MemoryError("not enough memory")

    assert monitoring._index_state["active"] is False
    assert monitoring._index_state["status"] == "Out of memory"
    assert monitoring._index_state["phase"] == "embedding"
