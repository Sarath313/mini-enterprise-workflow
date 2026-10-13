import time
import unittest
from unittest.mock import Mock, patch

from redis.exceptions import ConnectionError as RedisConnectionError

from app.core import dashboard_cache
from app.database import settings
from app.models.task import Task
from app.models.user import User
from app.schemas.dashboard import DashboardResponse


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.increments: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.values[key] = value
        self.ttls[key] = ttl

    def incr(self, key: str) -> int:
        value = self.increments.get(key, 0) + 1
        self.increments[key] = value
        self.values[key] = str(value)
        return value


class UnavailableRedis:
    def get(self, key: str) -> None:
        raise RedisConnectionError("test Redis unavailable")

    def setex(self, key: str, ttl: int, value: str) -> None:
        raise RedisConnectionError("test Redis unavailable")

    def incr(self, key: str) -> None:
        raise RedisConnectionError("test Redis unavailable")


class DashboardCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.redis = FakeRedis()
        self.response = DashboardResponse(
            total_tasks=2,
            todo_tasks=1,
            in_progress_tasks=0,
            done_tasks=1,
            low_priority_tasks=0,
            medium_priority_tasks=2,
            high_priority_tasks=0,
            assigned_tasks=1,
            unassigned_tasks=1,
            overdue_tasks=0,
        )

    def test_cache_hit_serializes_dashboard_with_configured_ttl(self) -> None:
        with (
            patch.object(settings, "REDIS_URL", "redis://cache.test/0"),
            patch.object(
                settings,
                "DASHBOARD_CACHE_TTL_SECONDS",
                37,
            ),
            patch.object(
                dashboard_cache,
                "_get_redis_client",
                return_value=self.redis,
            ),
        ):
            dashboard_cache.set_cached_dashboard(
                8,
                "manager",
                self.response,
            )
            cached = dashboard_cache.get_cached_dashboard(8, "manager")

        self.assertEqual(cached, self.response)
        self.assertEqual(
            self.redis.ttls["dashboard:0:user:8:role:manager"],
            37,
        )

    def test_dashboard_endpoint_uses_cache_before_querying_database(self) -> None:
        from app.routers.dashboard import get_dashboard

        user = User(
            id=8,
            name="Cache Test User",
            email="dashboard-cache@example.com",
            hashed_password="not-a-real-hash",
            role="manager",
            is_active=True,
        )
        db = Mock()
        db.query.side_effect = AssertionError(
            "database query should be skipped on a cache hit"
        )
        with patch.object(
            dashboard_cache,
            "_get_redis_client",
            return_value=self.redis,
        ):
            dashboard_cache.set_cached_dashboard(
                user.id,
                user.role,
                self.response,
            )
            result = get_dashboard(user, db)

        self.assertEqual(result, self.response)
        db.query.assert_not_called()

    def test_cache_entries_are_isolated_by_user_and_role(self) -> None:
        with patch.object(
            dashboard_cache,
            "_get_redis_client",
            return_value=self.redis,
        ):
            dashboard_cache.set_cached_dashboard(
                8,
                "manager",
                self.response,
            )
            user_result = dashboard_cache.get_cached_dashboard(
                9,
                "manager",
            )
            role_result = dashboard_cache.get_cached_dashboard(
                8,
                "admin",
            )
            owner_result = dashboard_cache.get_cached_dashboard(
                8,
                "manager",
            )

        self.assertIsNone(user_result)
        self.assertIsNone(role_result)
        self.assertEqual(owner_result, self.response)

    def test_invalidation_changes_cache_namespace(self) -> None:
        with patch.object(
            dashboard_cache,
            "_get_redis_client",
            return_value=self.redis,
        ):
            dashboard_cache.set_cached_dashboard(
                8,
                "manager",
                self.response,
            )
            dashboard_cache.invalidate_dashboard_cache()
            cached = dashboard_cache.get_cached_dashboard(8, "manager")

        self.assertIsNone(cached)
        self.assertEqual(
            self.redis.increments[dashboard_cache._CACHE_VERSION_KEY],
            1,
        )

    def test_redis_unavailability_falls_back_without_raising(self) -> None:
        with (
            patch.object(settings, "REDIS_URL", "redis://cache.test/0"),
            patch.object(
                dashboard_cache,
                "_get_redis_client",
                return_value=UnavailableRedis(),
            ),
        ):
            self.assertIsNone(
                dashboard_cache.get_cached_dashboard(8, "manager")
            )
            dashboard_cache.set_cached_dashboard(
                8,
                "manager",
                self.response,
            )
            dashboard_cache.invalidate_dashboard_cache()

    def test_dashboard_computes_live_data_when_redis_is_unavailable(self) -> None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from sqlalchemy.pool import StaticPool

        from app.database import Base
        from app.routers.dashboard import get_dashboard

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        db = Session(engine)
        try:
            user = User(
                name="Cache Test User",
                email=f"cache-{time.time_ns()}@example.com",
                hashed_password="not-a-real-hash",
                role="employee",
                is_active=True,
            )
            db.add(user)
            db.flush()
            db.add(
                Task(
                    title="Visible task",
                    status="todo",
                    priority="medium",
                    created_by=user.id,
                    assigned_to=user.id,
                )
            )
            db.commit()

            with (
                patch.object(settings, "REDIS_URL", "redis://cache.test/0"),
                patch.object(
                    dashboard_cache,
                    "_get_redis_client",
                    return_value=UnavailableRedis(),
                ),
            ):
                response = get_dashboard(user, db)

            self.assertEqual(response.total_tasks, 1)
            self.assertEqual(response.todo_tasks, 1)
        finally:
            db.close()
            engine.dispose()
