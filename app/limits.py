# app/limits.py
from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, DefaultDict, Tuple


@dataclass
class SlidingWindowLimiter:
    """
    In-memory sliding window limiter.
    Phase-1 için yeterli (restart'ta sıfırlanır).
    """
    per_minute: int
    window_seconds: int = 60

    _events: DefaultDict[str, Deque[float]] = None  # type: ignore

    def __post_init__(self) -> None:
        self._events = defaultdict(deque)

    def allow(self, key: str) -> Tuple[bool, int]:
        """
        returns: (allowed, retry_after_seconds)
        """
        now = time.time()
        q = self._events[key]

        # drop old events
        cutoff = now - self.window_seconds
        while q and q[0] < cutoff:
            q.popleft()

        if len(q) >= self.per_minute:
            retry_after = int((q[0] + self.window_seconds) - now) + 1
            return False, max(retry_after, 1)

        q.append(now)
        return True, 0
