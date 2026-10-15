"""Small in-memory sliding-window counters for the auth endpoints.

Per-process, like the global rate limiter in middleware.py: fine for a single instance, and a
Redis-backed version would be the upgrade for several. Memory is bounded by pruning idle keys.
"""
import time
from collections import defaultdict, deque

from app.core.exceptions import AppException


class SlidingWindowCounter:
    def __init__(self, max_events: int, window_seconds: float, prune_every: int = 500):
        self.max_events = max_events
        self.window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._calls = 0
        self._prune_every = prune_every

    def _trim(self, key: str, now: float) -> deque[float]:
        events = self._events[key]
        while events and events[0] <= now - self.window:
            events.popleft()
        return events

    def _prune(self, now: float) -> None:
        self._calls += 1
        if self._calls % self._prune_every:
            return
        for key in [k for k in self._events if not self._trim(k, now)]:
            del self._events[key]

    def count(self, key: str) -> int:
        now = time.monotonic()
        return len(self._trim(key, now))

    def record(self, key: str) -> None:
        now = time.monotonic()
        self._trim(key, now).append(now)
        self._prune(now)

    def reset(self, key: str) -> None:
        self._events.pop(key, None)

    def retry_after(self, key: str) -> int:
        events = self._events.get(key)
        if not events:
            return 0
        return max(1, int(events[0] + self.window - time.monotonic()) + 1)

    def enforce(self, key: str, message: str) -> None:
        """Raise 429 if `key` already used up its allowance in the current window."""
        if self.count(key) >= self.max_events:
            raise AppException(
                status_code=429,
                detail=f"{message} Try again in {max(1, self.retry_after(key) // 60)} minute(s).",
            )
