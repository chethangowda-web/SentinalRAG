import gc
import logging
import os

logger = logging.getLogger(__name__)

_has_psutil = False
try:
    import psutil
    _has_psutil = True
except ImportError:
    pass


def get_memory_rss_mb() -> float:
    if not _has_psutil:
        return 0.0
    try:
        proc = psutil.Process(os.getpid())
        return proc.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0


def log_memory_usage(step: str, previous_mb: float | None = None) -> float:
    current = get_memory_rss_mb()
    if previous_mb is not None and previous_mb > 0:
        delta = current - previous_mb
        logger.info("Memory [%s] RSS=%.1fMB (delta=%.1fMB)", step, current, delta)
    else:
        logger.info("Memory [%s] RSS=%.1fMB", step, current)
    return current


def force_gc() -> None:
    collected = gc.collect()
    logger.debug("Garbage collector: collected %d objects", collected)
