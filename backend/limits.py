from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Callable, Deque, Dict


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after: int = 0
    remaining: int = 0


class SlidingWindowRateLimiter:
    """In-memory rate limiter using a true sliding window."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.limit = max(0, int(limit))
        self.window_seconds = max(1, int(window_seconds))
        self._clock = clock
        self._events: Dict[str, Deque[float]] = {}
        self._lock = Lock()
        self._checks = 0

    def check(self, key: str) -> RateLimitDecision:
        if self.limit <= 0:
            return RateLimitDecision(allowed=True, remaining=0)

        now = self._clock()
        cutoff = now - self.window_seconds

        with self._lock:
            self._checks += 1
            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= self.limit:
                retry_after = max(1, math.ceil(self.window_seconds - (now - events[0])))
                return RateLimitDecision(allowed=False, retry_after=retry_after, remaining=0)

            events.append(now)
            remaining = max(0, self.limit - len(events))

            if self._checks % 256 == 0:
                self._cleanup_stale_locked(cutoff)

            return RateLimitDecision(allowed=True, remaining=remaining)

    def _cleanup_stale_locked(self, cutoff: float) -> None:
        stale_keys = []
        for key, events in self._events.items():
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                stale_keys.append(key)
        for key in stale_keys:
            self._events.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._checks = 0


class ClientConcurrencyLimiter:
    """Tracks active generation jobs per client within one app process."""

    def __init__(self, limit_per_client: int) -> None:
        self.limit_per_client = max(0, int(limit_per_client))
        self._active: Dict[str, int] = {}
        self._lock = Lock()

    def try_acquire(self, key: str) -> bool:
        if self.limit_per_client <= 0:
            return True

        with self._lock:
            active = self._active.get(key, 0)
            if active >= self.limit_per_client:
                return False
            self._active[key] = active + 1
            return True

    def release(self, key: str) -> None:
        if self.limit_per_client <= 0:
            return

        with self._lock:
            active = self._active.get(key, 0)
            if active <= 1:
                self._active.pop(key, None)
            else:
                self._active[key] = active - 1

    def active_for(self, key: str) -> int:
        with self._lock:
            return self._active.get(key, 0)

    def reset(self) -> None:
        with self._lock:
            self._active.clear()
