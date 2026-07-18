import asyncio
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ResourceSnapshot:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_rss_mb: float
    disk_usage_mb: float
    open_fds: int


@dataclass
class ResourceMetrics:
    cpu_avg: float
    cpu_max: float
    cpu_min: float
    memory_avg_mb: float
    memory_max_mb: float
    memory_min_mb: float
    memory_avg_percent: float
    memory_peak_percent: float
    disk_total_mb: float
    disk_used_mb: float
    disk_free_mb: float
    samples: int
    duration_seconds: float


class ResourceTracker:
    def __init__(self, interval: float = 1.0, max_samples: int = 3600):
        self.interval = interval
        self.max_samples = max_samples
        self.snapshots: deque[ResourceSnapshot] = deque(maxlen=max_samples)
        self._running = False
        self._start_time: float | None = None
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self.snapshots.clear()
        self._running = True
        self._start_time = time.time()
        self._task = asyncio.ensure_future(self._sample_loop())
        logger.info("Resource tracking started (interval=%ss, max_samples=%d)", self.interval, self.max_samples)

    async def _sample_loop(self) -> None:
        while self._running:
            self.sample()
            await asyncio.sleep(self.interval)

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Resource tracking stopped (%d samples collected)", len(self.snapshots))

    def sample(self) -> ResourceSnapshot | None:
        if not self._running:
            return None
        try:
            import psutil
            proc = psutil.Process(os.getpid())
            mem = proc.memory_info()
            cpu = proc.cpu_percent(interval=0)
            disk = psutil.disk_usage("/")
            snapshot = ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=cpu,
                memory_percent=proc.memory_percent(),
                memory_rss_mb=mem.rss / (1024 * 1024),
                disk_usage_mb=disk.used / (1024 * 1024),
                open_fds=proc.num_fds() if hasattr(proc, "num_fds") else 0,
            )
            self.snapshots.append(snapshot)
            return snapshot
        except ImportError:
            if len(self.snapshots) == 0:
                logger.warning("psutil not available — resource tracking disabled")
            return None
        except Exception as e:
            logger.debug("Resource sample failed: %s", e)
            return None

    def summarize(self) -> ResourceMetrics:
        if not self.snapshots:
            return ResourceMetrics(
                cpu_avg=0, cpu_max=0, cpu_min=0,
                memory_avg_mb=0, memory_max_mb=0, memory_min_mb=0,
                memory_avg_percent=0, memory_peak_percent=0,
                disk_total_mb=0, disk_used_mb=0, disk_free_mb=0,
                samples=0, duration_seconds=0,
            )
        cpus = [s.cpu_percent for s in self.snapshots]
        mems_mb = [s.memory_rss_mb for s in self.snapshots]
        mems_pct = [s.memory_percent for s in self.snapshots]

        try:
            import psutil
            disk = psutil.disk_usage("/")
            disk_total = disk.total / (1024 * 1024)
            disk_used = disk.used / (1024 * 1024)
            disk_free = disk.free / (1024 * 1024)
        except Exception:
            disk_total = disk_used = disk_free = 0

        duration = (self.snapshots[-1].timestamp - self.snapshots[0].timestamp) if len(self.snapshots) > 1 else 0

        return ResourceMetrics(
            cpu_avg=sum(cpus) / len(cpus),
            cpu_max=max(cpus),
            cpu_min=min(cpus),
            memory_avg_mb=sum(mems_mb) / len(mems_mb),
            memory_max_mb=max(mems_mb),
            memory_min_mb=min(mems_mb),
            memory_avg_percent=sum(mems_pct) / len(mems_pct),
            memory_peak_percent=max(mems_pct),
            disk_total_mb=disk_total,
            disk_used_mb=disk_used,
            disk_free_mb=disk_free,
            samples=len(self.snapshots),
            duration_seconds=duration,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "samples": len(self.snapshots),
            "summary": {
                "cpu_avg": round(sum(s.cpu_percent for s in self.snapshots) / len(self.snapshots), 2) if self.snapshots else 0,
                "cpu_max": round(max(s.cpu_percent for s in self.snapshots), 2) if self.snapshots else 0,
                "memory_avg_mb": round(sum(s.memory_rss_mb for s in self.snapshots) / len(self.snapshots), 2) if self.snapshots else 0,
                "memory_max_mb": round(max(s.memory_rss_mb for s in self.snapshots), 2) if self.snapshots else 0,
                "memory_peak_percent": round(max(s.memory_percent for s in self.snapshots), 2) if self.snapshots else 0,
            },
            "snapshots": [
                {
                    "timestamp": s.timestamp,
                    "cpu_percent": round(s.cpu_percent, 2),
                    "memory_rss_mb": round(s.memory_rss_mb, 2),
                    "memory_percent": round(s.memory_percent, 2),
                    "disk_usage_mb": round(s.disk_usage_mb, 2),
                    "open_fds": s.open_fds,
                }
                for s in self.snapshots
            ],
        }


_resource_tracker: ResourceTracker | None = None


def get_resource_tracker() -> ResourceTracker:
    global _resource_tracker
    if _resource_tracker is None:
        _resource_tracker = ResourceTracker()
    return _resource_tracker
