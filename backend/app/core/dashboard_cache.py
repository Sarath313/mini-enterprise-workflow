import logging

from pydantic import ValidationError
from redis import Redis
from redis.exceptions import RedisError

from app.database import settings
from app.schemas.dashboard import DashboardResponse


logger = logging.getLogger(__name__)

_CACHE_VERSION_KEY = "dashboard:cache-version"
_redis_client: Redis | None = None
_redis_client_url: str | None = None


def _get_redis_client() -> Redis | None:
    global _redis_client, _redis_client_url

    redis_url = settings.REDIS_URL
    if not redis_url:
        return None

    if _redis_client is None or _redis_client_url != redis_url:
        _redis_client = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        _redis_client_url = redis_url

    return _redis_client


def _cache_key(user_id: int, role: str, version: str) -> str:
    return f"dashboard:{version}:user:{user_id}:role:{role}"


def get_cached_dashboard(
    user_id: int,
    role: str,
) -> DashboardResponse | None:
    try:
        client = _get_redis_client()
        if client is None:
            return None

        version = client.get(_CACHE_VERSION_KEY) or "0"
        payload = client.get(_cache_key(user_id, role, version))
        if payload is None:
            return None
        return DashboardResponse.model_validate_json(payload)
    except (RedisError, ValidationError, ValueError):
        logger.warning("Dashboard cache read failed; computing live data")
        return None


def set_cached_dashboard(
    user_id: int,
    role: str,
    response: DashboardResponse,
) -> None:
    try:
        client = _get_redis_client()
        if client is None:
            return

        version = client.get(_CACHE_VERSION_KEY) or "0"
        client.setex(
            _cache_key(user_id, role, version),
            settings.DASHBOARD_CACHE_TTL_SECONDS,
            response.model_dump_json(),
        )
    except RedisError:
        logger.warning("Dashboard cache write failed; serving live data")


def invalidate_dashboard_cache() -> None:
    try:
        client = _get_redis_client()
        if client is not None:
            client.incr(_CACHE_VERSION_KEY)
    except RedisError:
        logger.warning("Dashboard cache invalidation failed")
