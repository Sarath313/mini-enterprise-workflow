import hashlib
import logging
import math
import threading
import time
from collections.abc import Callable
from typing import Protocol

from fastapi import HTTPException, Request, status
from redis import Redis
from redis.exceptions import RedisError

from app.database import settings


logger = logging.getLogger(__name__)

_REDIS_FIXED_WINDOW_SCRIPT = """
local count = redis.call("INCR", KEYS[1])
if count == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end
return {count, redis.call("TTL", KEYS[1])}
"""


class RateLimitStore(Protocol):
    def consume(
        self,
        key: str,
        window_seconds: int,
    ) -> tuple[int, int]: ...


class InMemoryRateLimitStore:
    """Process-local limiter for development and isolated tests."""

    def __init__(self) -> None:
        self._buckets: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def consume(
        self,
        key: str,
        window_seconds: int,
    ) -> tuple[int, int]:
        now = time.monotonic()
        window_start = math.floor(now / window_seconds) * window_seconds
        expires_at = window_start + window_seconds

        with self._lock:
            expired = [
                bucket_key
                for bucket_key, (_, expiry) in self._buckets.items()
                if expiry <= now
            ]
            for bucket_key in expired:
                del self._buckets[bucket_key]

            count, bucket_expiry = self._buckets.get(
                key,
                (0, expires_at),
            )
            if bucket_expiry <= now:
                count = 0
                bucket_expiry = expires_at

            count += 1
            self._buckets[key] = (count, bucket_expiry)
            retry_after = max(1, math.ceil(bucket_expiry - now))
            return count, retry_after


class RedisRateLimitStore:
    """Shared fixed-window limiter for multi-worker deployments."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    def consume(
        self,
        key: str,
        window_seconds: int,
    ) -> tuple[int, int]:
        result = self._client.eval(
            _REDIS_FIXED_WINDOW_SCRIPT,
            1,
            key,
            window_seconds,
        )
        return int(result[0]), max(1, int(result[1]))


_memory_store = InMemoryRateLimitStore()
_redis_store: RedisRateLimitStore | None = None
_redis_store_url: str | None = None
_store_lock = threading.Lock()


def _get_store() -> RateLimitStore:
    global _redis_store, _redis_store_url

    redis_url = settings.RATE_LIMIT_REDIS_URL
    if not redis_url:
        if settings.APP_ENV.lower() == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting is not configured",
            )
        return _memory_store

    with _store_lock:
        if _redis_store is None or _redis_store_url != redis_url:
            client = Redis.from_url(redis_url, decode_responses=True)
            _redis_store = RedisRateLimitStore(client)
            _redis_store_url = redis_url
        return _redis_store


def rate_limit(
    scope: str,
    max_requests: int | Callable[[], int],
    window_seconds: int | Callable[[], int],
) -> Callable[[Request], None]:
    def check(request: Request) -> None:
        request_limit = (
            max_requests() if callable(max_requests) else max_requests
        )
        request_window = (
            window_seconds() if callable(window_seconds) else window_seconds
        )
        client_host = (
            request.client.host
            if request.client is not None
            else "unknown"
        )
        host_hash = hashlib.sha256(
            client_host.encode("utf-8")
        ).hexdigest()
        key = f"rate-limit:{scope}:{host_hash}"

        try:
            count, retry_after = _get_store().consume(
                key,
                request_window,
            )
        except RedisError:
            logger.exception("Rate-limit Redis backend is unavailable")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting is temporarily unavailable",
            ) from None

        if count > request_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={"Retry-After": str(retry_after)},
            )

    return check
