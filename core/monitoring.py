"""Cross-platform host and indexing resource metrics."""

from contextlib import contextmanager
from pathlib import Path
import threading
import time

import psutil

from core.config import cfg


_process = psutil.Process()
_monitor_lock = threading.Lock()
_index_state = {
    "active": False,
    "source": None,
    "phase": None,
    "progress": None,
    "started_at": None,
    "elapsed_seconds": 0.0,
    "cpu_percent": 0.0,
    "memory_mb": 0.0,
    "peak_cpu_percent": 0.0,
    "peak_memory_mb": 0.0,
    "status": "Idle",
    "last_error": None,
}


def _cgroup_memory() -> tuple[int | None, int | None]:
    """Return a Linux container memory limit and current use, when available."""
    candidates = (
        (Path("/sys/fs/cgroup/memory.max"), Path("/sys/fs/cgroup/memory.current")),
        (
            Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
            Path("/sys/fs/cgroup/memory/memory.usage_in_bytes"),
        ),
    )
    for limit_path, usage_path in candidates:
        try:
            limit_text = limit_path.read_text(encoding="ascii").strip()
            usage_text = usage_path.read_text(encoding="ascii").strip()
        except OSError:
            continue
        if limit_text == "max":
            continue
        try:
            limit, usage = int(limit_text), int(usage_text)
        except ValueError:
            continue
        if 0 < limit < 1 << 60:
            return limit, max(0, usage)
    return None, None


def _cgroup_cpu_limit() -> float | None:
    """Return a Linux container CPU quota in cores, when one is configured."""
    quota_files = (
        (Path("/sys/fs/cgroup/cpu.max"), None),
        (
            Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us"),
            Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us"),
        ),
    )
    for quota_path, period_path in quota_files:
        try:
            if period_path is None:
                quota, period = quota_path.read_text(encoding="ascii").split()
            else:
                quota = quota_path.read_text(encoding="ascii").strip()
                period = period_path.read_text(encoding="ascii").strip()
            if quota == "max":
                continue
            quota_value, period_value = int(quota), int(period)
        except (OSError, ValueError):
            continue
        if quota_value > 0 and period_value > 0:
            return quota_value / period_value
    return None


def _storage_path() -> Path:
    path = Path(cfg.db_path).resolve()
    while not path.exists() and path != path.parent:
        path = path.parent
    return path


def resource_snapshot() -> dict:
    """Collect current system, process, and database-volume capacity metrics."""
    memory = psutil.virtual_memory()
    cgroup_limit, cgroup_usage = _cgroup_memory()
    memory_total = min(memory.total, cgroup_limit) if cgroup_limit else memory.total
    memory_available = (
        min(memory.available, max(0, cgroup_limit - cgroup_usage))
        if cgroup_limit is not None and cgroup_usage is not None
        else memory.available
    )
    disk = psutil.disk_usage(str(_storage_path()))
    cpu_count = psutil.cpu_count(logical=True) or 1
    try:
        cpu_cores_available = len(_process.cpu_affinity())
    except (AttributeError, OSError, psutil.Error):
        cpu_cores_available = cpu_count
    cpu_quota = _cgroup_cpu_limit()
    if cpu_quota is not None:
        cpu_cores_available = min(cpu_cores_available, cpu_quota)
    process_cpu = _process.cpu_percent(interval=None)
    process_memory = _process.memory_info().rss
    system_cpu = psutil.cpu_percent(interval=None)

    with _monitor_lock:
        _index_state["cpu_percent"] = process_cpu
        _index_state["memory_mb"] = process_memory / (1024**2)
        if _index_state["active"]:
            _index_state["peak_cpu_percent"] = max(
                _index_state["peak_cpu_percent"], process_cpu
            )
            _index_state["peak_memory_mb"] = max(
                _index_state["peak_memory_mb"],
                _index_state["memory_mb"],
            )
        indexing = dict(_index_state)
        if indexing["active"] and indexing["started_at"] is not None:
            indexing["elapsed_seconds"] = time.monotonic() - indexing["started_at"]

    return {
        "cpu_cores": cpu_count,
        "cpu_cores_available": cpu_cores_available,
        "cpu_quota": cpu_quota,
        "system_cpu_percent": system_cpu,
        "memory_total_bytes": memory_total,
        "memory_available_bytes": memory_available,
        "memory_used_bytes": max(0, memory_total - memory_available),
        "memory_limit_bytes": cgroup_limit,
        "disk_total_bytes": disk.total,
        "disk_free_bytes": disk.free,
        "disk_used_bytes": disk.used,
        "indexing": indexing,
    }


def is_out_of_memory_error(error: BaseException) -> bool:
    """Recognize Python and common native-library allocation failures."""
    if isinstance(error, MemoryError):
        return True
    message = str(error).lower()
    return any(
        phrase in message
        for phrase in (
            "out of memory",
            "cannot allocate memory",
            "can't allocate memory",
            "not enough memory",
            "bad alloc",
        )
    )


@contextmanager
def track_indexing(source: str):
    """Track indexing resource use and preserve errors for the caller."""
    with _monitor_lock:
        _index_state.update(
            active=True,
            source=source,
            phase="Starting",
            progress=None,
            started_at=time.monotonic(),
            elapsed_seconds=0.0,
            peak_cpu_percent=0.0,
            peak_memory_mb=0.0,
            status="Indexing",
            last_error=None,
        )

    def report_progress(phase: str, current: int, total: int) -> None:
        with _monitor_lock:
            _index_state["phase"] = phase
            _index_state["progress"] = (current, total)
        resource_snapshot()

    try:
        yield report_progress
    except Exception as error:
        with _monitor_lock:
            _index_state["status"] = (
                "Out of memory" if is_out_of_memory_error(error) else "Failed"
            )
            _index_state["last_error"] = str(error)
        raise
    else:
        with _monitor_lock:
            _index_state["status"] = "Completed"
    finally:
        with _monitor_lock:
            _index_state["active"] = False
            started_at = _index_state["started_at"]
            if started_at is not None:
                _index_state["elapsed_seconds"] = time.monotonic() - started_at
            _index_state["started_at"] = None


def format_bytes(value: int) -> str:
    """Format a byte count using binary units."""
    amount = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{amount:.1f} TB"
