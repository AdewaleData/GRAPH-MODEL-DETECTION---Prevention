"""In-memory sliding-window rate limiter (optional Redis extension point)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from .config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS


class RateLimiter:
    """
    DSA: hash map client_id -> queue of request timestamps.
    Queue supports O(1) amortized prune of expired entries.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, client_id: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[client_id]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.max_requests:
                return False
            q.append(now)
            return True


rate_limiter = RateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)
