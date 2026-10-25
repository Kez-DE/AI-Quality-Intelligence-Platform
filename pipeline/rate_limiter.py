"""In-memory sliding window rate limiter for FastAPI.

Dùng làm dependency để giới hạn số request theo scope; staff/admin/manager được
bypass hoàn toàn. Route không có tài khoản (public intake) và các tầng chat gọi
thẳng check_rate_limit(limiter, key) với key tự chọn.

Cách dùng:
    from rate_limiter import RateLimiter

    report_limit = RateLimiter(max_requests=10, window_seconds=3600, scope="report")

    @app.post("/api/example")
    def example(
        user: AuthUser = Depends(get_current_user),
        _: None = Depends(report_limit),
    ):
        ...

Preset instances:
    - general_api_limit:   100 req / minute
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request

from auth_guard import AuthUser, get_current_user

# Roles that bypass rate limiting entirely.
BYPASS_ROLES = {"admin", "manager", "staff"}


class RateLimiter:
    """Sliding window rate limiter implemented as a FastAPI dependency.

    Parameters
    ----------
    max_requests : int
        Maximum number of allowed requests within the window.
    window_seconds : int
        Length of the sliding window in seconds.
    scope : str
        Logical name for this limiter (used in error messages and to
        separate counters — e.g. "feedback", "chat", "general").
    """

    def __init__(self, max_requests: int, window_seconds: int, scope: str = "default") -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.scope = scope

        # {user_id: deque of timestamps}
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._check_count = 0

    # ------------------------------------------------------------------
    # FastAPI dependency interface
    # ------------------------------------------------------------------

    async def __call__(
        self,
        request: Request,
        user: AuthUser = Depends(get_current_user),
    ) -> None:
        """Check rate limit. Raises HTTP 429 if exceeded."""

        # Staff/admin/manager are never rate-limited.
        if user.role in BYPASS_ROLES:
            return

        now = time.time()
        user_key = f"{user.id}:{self.scope}"

        with self._lock:
            self._check_count += 1

            # Periodic cleanup every 100 checks to prevent memory creep.
            if self._check_count % 100 == 0:
                self._cleanup(now)

            bucket = self._requests[user_key]

            # Remove timestamps outside the current window.
            cutoff = now - self.window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                # Calculate when the earliest request expires.
                retry_after = int(bucket[0] + self.window_seconds - now) + 1
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Rate limit exceeded for scope '{self.scope}'. "
                        f"Max {self.max_requests} requests per {self._format_window()}. "
                        f"Try again in {retry_after}s."
                    ),
                    headers={"Retry-After": str(retry_after)},
                )

            # Record this request.
            bucket.append(now)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cleanup(self, now: float) -> None:
        """Remove all entries older than the window. Called under lock."""
        cutoff = now - self.window_seconds
        stale_keys: list[str] = []
        for key, bucket in self._requests.items():
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if not bucket:
                stale_keys.append(key)
        for key in stale_keys:
            del self._requests[key]

    def _format_window(self) -> str:
        """Human-readable window description."""
        if self.window_seconds >= 3600:
            hours = self.window_seconds / 3600
            return f"{hours:g} hour{'s' if hours != 1 else ''}"
        minutes = self.window_seconds / 60
        return f"{minutes:g} minute{'s' if minutes != 1 else ''}"


# ------------------------------------------------------------------
# Pre-configured instances for common use cases
# ------------------------------------------------------------------

# General API calls: 100 per minute (applies to any user scope)
general_api_limit = RateLimiter(max_requests=100, window_seconds=60, scope="general")


def check_rate_limit(limiter: RateLimiter, user_id: str) -> None:
    """Synchronous rate-limit check for use inside endpoint bodies.

    Unlike the async __call__ dependency interface, this is a simple function
    that raises HTTP 429 directly when the limit is exceeded.
    """
    import time as _time

    now = _time.time()
    user_key = f"{user_id}:{limiter.scope}"

    with limiter._lock:
        limiter._check_count += 1
        if limiter._check_count % 100 == 0:
            limiter._cleanup(now)

        bucket = limiter._requests[user_key]
        cutoff = now - limiter.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= limiter.max_requests:
            retry_after = int(bucket[0] + limiter.window_seconds - now) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded for scope '{limiter.scope}'. "
                    f"Max {limiter.max_requests} requests per {limiter._format_window()}. "
                    f"Try again in {retry_after}s."
                ),
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
