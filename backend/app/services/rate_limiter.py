import time
from collections import defaultdict
from threading import Lock
from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """
    Stateless, in-memory sliding window rate limiter.
    Zero filesystem dependence, zero external service requirement.
    Thread-safe and automatically purges stale records.
    """

    def __init__(self):
        self._history = defaultdict(list)
        self._lock = Lock()
        self._last_cleanup = time.time()

    def _cleanup(self, now: float):
        # Prune dead keys periodically every 10 minutes
        if now - self._last_cleanup > 600:
            for key in list(self._history.keys()):
                self._history[key] = [t for t in self._history[key] if now - t < 3600]
                if not self._history[key]:
                    del self._history[key]
            self._last_cleanup = now

    def check(self, key: str, max_requests: int, window_seconds: int, action_name: str):
        now = time.time()
        with self._lock:
            self._cleanup(now)
            timestamps = self._history[key]
            # Retain only timestamps within the active sliding window
            valid_timestamps = [t for t in timestamps if now - t < window_seconds]
            if len(valid_timestamps) >= max_requests:
                retry_after = int(window_seconds - (now - valid_timestamps[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many {action_name} requests. Rate limit is {max_requests} per {window_seconds // 60 if window_seconds >= 60 else window_seconds}s. Try again in {retry_after}s.",
                    headers={"Retry-After": str(max(1, retry_after))},
                )
            valid_timestamps.append(now)
            self._history[key] = valid_timestamps


rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """
    Extract real client IP respecting X-Forwarded-For headers from reverse proxies (e.g. Render).
    Behind Render, the leftmost IP in X-Forwarded-For is the original client IP.
    """
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
