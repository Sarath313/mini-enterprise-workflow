import asyncio
import json
import time
import unittest
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from urllib.parse import urlencode
from unittest.mock import patch

from fastapi import HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core import rate_limit as rate_limit_module
from app.core.security import verify_password
from app.core.rate_limit import RedisRateLimitStore
from app.database import Base, Settings, get_db, settings
from app.dependencies.auth import (
    get_current_user,
    require_admin,
    require_manager_or_admin,
)
from app.models.approval import Approval
from app.models.approval_history import ApprovalHistory
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.notification import Notification
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.task import Task
from app.models.user import User
from app.main import app
from app.routers.auth import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    create_user_access_token,
    forgot_password,
    revoke_refresh_token,
    rotate_refresh_token,
    reset_password,
)
from app.routers.auth import router as auth_router
from app.routers.approvals import get_approval_history, get_task_approvals
from app.routers.audit_logs import get_audit_logs
from app.routers.documents import get_task_documents
from app.routers.notifications import get_notifications
from app.routers.tasks import get_tasks
from app.routers.users import get_users
from app.core.refresh_tokens import (
    generate_refresh_token,
    hash_refresh_token,
)

__import__("app.models")


class AuthSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = Session(self.engine)
        self.user = User(
            name="Test User",
            email=f"security-{time.time_ns()}@example.com",
            hashed_password="test-hash",
            role="employee",
            is_active=True,
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

    def tearDown(self) -> None:
        self.db.close()

    def add_refresh_token(self, raw_token: str | None = None) -> str:
        token = raw_token or generate_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=self.user.id,
                token_hash=hash_refresh_token(token),
                expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        self.db.commit()
        return token

    @staticmethod
    def asgi_request(
        method: str,
        path: str,
        body: bytes = b"",
        headers: list[tuple[bytes, bytes]] | None = None,
        query_string: bytes = b"",
    ) -> tuple[int, dict, dict]:
        messages = []
        received = False

        async def receive():
            nonlocal received
            if received:
                return {"type": "http.disconnect"}
            received = True
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query_string,
            "root_path": "",
            "headers": [(b"host", b"testserver"), *(headers or [])],
            "client": ("192.0.2.44", 1234),
            "server": ("testserver", 80),
            "state": {},
            "extensions": {},
        }
        asyncio.run(app(scope, receive, send))
        response_start = next(
            message
            for message in messages
            if message["type"] == "http.response.start"
        )
        response_body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        response_headers = dict(response_start["headers"])
        response_headers[b"set-cookie-all"] = tuple(
            value
            for key, value in response_start["headers"]
            if key == b"set-cookie"
        )
        return (
            response_start["status"],
            response_headers,
            json.loads(response_body) if response_body else {},
        )

    @staticmethod
    def response_cookies(headers: dict) -> dict:
        cookies = {}
        for value in headers.get(b"set-cookie-all", ()):
            parsed = SimpleCookie()
            parsed.load(value.decode("latin-1"))
            cookies.update(parsed)
        return cookies

    def post_auth_with_cookies(
        self,
        path: str,
        refresh_token: str,
        csrf_token: str,
        csrf_header: str | None = None,
    ):
        headers = [
            (
                b"cookie",
                (
                    f"refresh_token={refresh_token}; "
                    f"csrf_token={csrf_token}"
                ).encode("ascii"),
            )
        ]
        if csrf_header is not None:
            headers.append(
                (b"x-csrf-token", csrf_header.encode("ascii"))
            )
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        try:
            return self.asgi_request("POST", path, headers=headers)
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

    def post_form(self, path: str, values: dict[str, str]):
        return self.asgi_request(
            "POST",
            path,
            urlencode(values).encode("utf-8"),
            [(b"content-type", b"application/x-www-form-urlencoded")],
        )

    def test_access_token_uses_configured_expiry(self) -> None:
        original_expiry = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        try:
            settings.ACCESS_TOKEN_EXPIRE_MINUTES = 3
            token = create_user_access_token(self.user)
        finally:
            settings.ACCESS_TOKEN_EXPIRE_MINUTES = original_expiry

        from jose import jwt

        expiration = jwt.get_unverified_claims(token)["exp"]
        remaining = expiration - int(time.time())
        self.assertGreaterEqual(remaining, 178)
        self.assertLessEqual(remaining, 180)

    def test_refresh_rotates_token_and_rejects_reuse(self) -> None:
        old_token = self.add_refresh_token()

        response = rotate_refresh_token(old_token, self.db)

        old_record = (
            self.db.query(RefreshToken)
            .filter_by(token_hash=hash_refresh_token(old_token))
            .one()
        )
        new_record = (
            self.db.query(RefreshToken)
            .filter_by(token_hash=hash_refresh_token(response["refresh_token"]))
            .one()
        )
        self.assertIsNotNone(old_record.revoked_at)
        self.assertIsNone(new_record.revoked_at)
        with self.assertRaises(HTTPException) as raised:
            rotate_refresh_token(old_token, self.db)
        self.assertEqual(raised.exception.status_code, 401)

    def test_expired_refresh_token_is_revoked_and_rejected(self) -> None:
        token = generate_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=self.user.id,
                token_hash=hash_refresh_token(token),
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            )
        )
        self.db.commit()

        with self.assertRaises(HTTPException) as raised:
            rotate_refresh_token(token, self.db)

        self.assertEqual(raised.exception.status_code, 401)
        record = (
            self.db.query(RefreshToken)
            .filter_by(token_hash=hash_refresh_token(token))
            .one()
        )
        self.assertIsNotNone(record.revoked_at)

    def test_logout_revokes_refresh_token(self) -> None:
        token = self.add_refresh_token()

        revoke_refresh_token(token, self.db)

        record = (
            self.db.query(RefreshToken)
            .filter_by(token_hash=hash_refresh_token(token))
            .one()
        )
        self.assertIsNotNone(record.revoked_at)

    def test_password_reset_is_single_use_and_revokes_refresh_tokens(self) -> None:
        raw_token = generate_refresh_token()
        self.db.add(
            PasswordResetToken(
                user_id=self.user.id,
                token_hash=hash_refresh_token(raw_token),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            )
        )
        refresh_token = self.add_refresh_token()

        response = reset_password(
            ResetPasswordRequest(
                token=raw_token,
                new_password="a sufficiently long test password",
            ),
            self.db,
        )

        self.assertEqual(response["message"], "Password reset successful")
        self.assertTrue(
            verify_password(
                "a sufficiently long test password",
                self.user.hashed_password,
            )
        )
        reset_record = (
            self.db.query(PasswordResetToken)
            .filter_by(token_hash=hash_refresh_token(raw_token))
            .one()
        )
        refresh_record = (
            self.db.query(RefreshToken)
            .filter_by(token_hash=hash_refresh_token(refresh_token))
            .one()
        )
        self.assertIsNotNone(reset_record.used_at)
        self.assertIsNotNone(refresh_record.revoked_at)
        with self.assertRaises(HTTPException) as raised:
            reset_password(
                ResetPasswordRequest(
                    token=raw_token,
                    new_password="another sufficiently long password",
                ),
                self.db,
            )
        self.assertEqual(raised.exception.status_code, 400)

    def test_expired_password_reset_token_is_rejected_and_invalidated(self) -> None:
        raw_token = generate_refresh_token()
        self.db.add(
            PasswordResetToken(
                user_id=self.user.id,
                token_hash=hash_refresh_token(raw_token),
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            )
        )
        self.db.commit()

        with self.assertRaises(HTTPException) as raised:
            reset_password(
                ResetPasswordRequest(
                    token=raw_token,
                    new_password="a sufficiently long test password",
                ),
                self.db,
            )

        self.assertEqual(raised.exception.status_code, 400)
        record = (
            self.db.query(PasswordResetToken)
            .filter_by(token_hash=hash_refresh_token(raw_token))
            .one()
        )
        self.assertIsNotNone(record.used_at)

    def test_forgot_password_uses_configured_token_expiry(self) -> None:
        original_expiry = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 7
        try:
            with patch(
                "app.routers.auth.deliver_password_reset_token"
            ) as deliver:
                result = forgot_password(
                    ForgotPasswordRequest(email=self.user.email),
                    self.db,
                )
        finally:
            settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = original_expiry

        record = (
            self.db.query(PasswordResetToken)
            .filter_by(user_id=self.user.id)
            .one()
        )
        lifetime = (
            record.expires_at.replace(tzinfo=timezone.utc)
            - record.created_at.replace(tzinfo=timezone.utc)
        )
        self.assertIn("message", result)
        self.assertNotIn("token", result)
        self.assertNotIn("access_token", result)
        self.assertNotIn("refresh_token", result)
        self.assertLessEqual(lifetime, timedelta(minutes=7))
        self.assertGreater(
            lifetime,
            timedelta(minutes=7) - timedelta(seconds=1),
        )
        deliver.assert_called_once()

    def test_forgot_password_keeps_generic_response_for_unknown_email(
        self,
    ) -> None:
        with patch("app.routers.auth.deliver_password_reset_token") as deliver:
            result = forgot_password(
                ForgotPasswordRequest(email="unknown@example.com"),
                self.db,
            )

        self.assertEqual(
            result,
            {
                "message": (
                    "If the account exists and email delivery is configured, "
                    "password reset instructions will be sent."
                )
            },
        )
        deliver.assert_not_called()

    def test_login_sets_http_only_refresh_and_signed_csrf_cookies(self) -> None:
        from app.core.security import hash_password

        self.user.hashed_password = hash_password(
            "a sufficiently long login password"
        )
        self.db.commit()
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        try:
            status_code, headers, response = self.post_form(
                "/auth/login",
                {
                    "username": self.user.email,
                    "password": "a sufficiently long login password",
                },
            )
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

        self.assertEqual(status_code, 200)
        self.assertEqual(response["token_type"], "bearer")
        self.assertTrue(response["access_token"])
        self.assertNotIn("refresh_token", response)
        cookies = self.response_cookies(headers)
        refresh_cookie = cookies["refresh_token"]
        csrf_cookie = cookies["csrf_token"]
        raw_cookies = headers[b"set-cookie-all"]
        refresh_header = next(
            value for value in raw_cookies
            if value.startswith(b"refresh_token=")
        )
        csrf_header = next(
            value for value in raw_cookies
            if value.startswith(b"csrf_token=")
        )
        self.assertIn(b"; HttpOnly", refresh_header)
        self.assertIn(b"; HttpOnly", csrf_header)
        self.assertEqual(refresh_cookie["path"], "/auth")
        self.assertEqual(refresh_cookie["samesite"].lower(), "lax")
        self.assertEqual(csrf_cookie["path"], "/")
        self.assertEqual(response["csrf_token"], csrf_cookie.value)
        refresh_record = (
            self.db.query(RefreshToken)
            .filter_by(
                token_hash=hash_refresh_token(refresh_cookie.value)
            )
            .one()
        )
        self.assertEqual(refresh_record.user_id, self.user.id)

    def test_secure_setting_marks_both_auth_cookies_secure(self) -> None:
        from app.routers.auth import _set_auth_cookies
        from starlette.responses import Response

        original_secure = settings.REFRESH_COOKIE_SECURE
        settings.REFRESH_COOKIE_SECURE = True
        try:
            response = Response()
            _set_auth_cookies(response, generate_refresh_token())
        finally:
            settings.REFRESH_COOKIE_SECURE = original_secure

        cookies = response.raw_headers
        set_cookie_headers = [
            value for name, value in cookies if name == b"set-cookie"
        ]
        self.assertEqual(len(set_cookie_headers), 2)
        self.assertTrue(
            all(b"; Secure" in value for value in set_cookie_headers)
        )
        self.assertTrue(
            all(b"Domain=" not in value for value in set_cookie_headers)
        )

    def test_csrf_bootstrap_returns_token_and_sets_http_only_cookie(self):
        status_code, headers, response = self.asgi_request(
            "GET",
            "/auth/csrf",
        )

        self.assertEqual(status_code, 200)
        self.assertNotIn("refresh_token", response)
        csrf_cookie = self.response_cookies(headers)["csrf_token"]
        self.assertEqual(response["csrf_token"], csrf_cookie.value)
        self.assertIn(
            b"; HttpOnly",
            next(
                value
                for value in headers[b"set-cookie-all"]
                if value.startswith(b"csrf_token=")
            ),
        )

    def test_refresh_endpoint_rotates_cookie_and_never_returns_refresh_token(
        self,
    ) -> None:
        old_token = self.add_refresh_token()
        csrf_token = self.new_csrf_token()

        status_code, headers, response = self.post_auth_with_cookies(
            "/auth/refresh",
            old_token,
            csrf_token,
            csrf_token,
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(response["access_token"])
        self.assertNotIn("refresh_token", response)
        rotated_cookie = self.response_cookies(headers)["refresh_token"]
        self.assertNotEqual(rotated_cookie.value, old_token)
        old_record = (
            self.db.query(RefreshToken)
            .filter_by(token_hash=hash_refresh_token(old_token))
            .one()
        )
        self.assertIsNotNone(old_record.revoked_at)
        self.assertIsNotNone(
            self.db.query(RefreshToken)
            .filter_by(token_hash=hash_refresh_token(rotated_cookie.value))
            .one()
        )

        replay_status, _, _ = self.post_auth_with_cookies(
            "/auth/refresh",
            old_token,
            csrf_token,
            csrf_token,
        )
        self.assertEqual(replay_status, 401)

    def test_refresh_and_logout_require_valid_csrf_and_logout_clears_cookies(
        self,
    ) -> None:
        token = self.add_refresh_token()
        csrf_token = self.new_csrf_token()

        rejected_refresh, _, _ = self.post_auth_with_cookies(
            "/auth/refresh",
            token,
            csrf_token,
            "incorrect-csrf-token",
        )
        rejected_logout, _, _ = self.post_auth_with_cookies(
            "/auth/logout",
            token,
            csrf_token,
            "incorrect-csrf-token",
        )
        self.assertEqual(rejected_refresh, 403)
        self.assertEqual(rejected_logout, 403)
        record = (
            self.db.query(RefreshToken)
            .filter_by(token_hash=hash_refresh_token(token))
            .one()
        )
        self.assertIsNone(record.revoked_at)

        logout_status, headers, response = self.post_auth_with_cookies(
            "/auth/logout",
            token,
            csrf_token,
            csrf_token,
        )
        self.assertEqual(logout_status, 200)
        self.assertEqual(response["message"], "Logged out")
        self.assertIsNotNone(record.revoked_at)
        cleared = self.response_cookies(headers)
        self.assertEqual(cleared["refresh_token"]["max-age"], "0")
        self.assertEqual(cleared["csrf_token"]["max-age"], "0")

    def test_refresh_rejects_matching_but_unsigned_csrf_cookie_and_header(
        self,
    ) -> None:
        token = self.add_refresh_token()
        status_code, _, _ = self.post_auth_with_cookies(
            "/auth/refresh",
            token,
            "attacker-controlled-token",
            "attacker-controlled-token",
        )

        self.assertEqual(status_code, 403)
        record = (
            self.db.query(RefreshToken)
            .filter_by(token_hash=hash_refresh_token(token))
            .one()
        )
        self.assertIsNone(record.revoked_at)

    def test_refresh_endpoint_revokes_expired_cookie_and_clears_it(self) -> None:
        token = generate_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=self.user.id,
                token_hash=hash_refresh_token(token),
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            )
        )
        self.db.commit()
        csrf_token = self.new_csrf_token()

        status_code, headers, _ = self.post_auth_with_cookies(
            "/auth/refresh",
            token,
            csrf_token,
            csrf_token,
        )

        self.assertEqual(status_code, 401)
        record = (
            self.db.query(RefreshToken)
            .filter_by(token_hash=hash_refresh_token(token))
            .one()
        )
        self.assertIsNotNone(record.revoked_at)
        self.assertEqual(
            self.response_cookies(headers)["refresh_token"]["max-age"],
            "0",
        )

    @staticmethod
    def new_csrf_token() -> str:
        from app.routers.auth import _create_csrf_token

        return _create_csrf_token()

    def test_role_dependencies_allow_only_expected_roles(self) -> None:
        with self.assertRaises(HTTPException):
            require_manager_or_admin(self.user)
        with self.assertRaises(HTTPException) as raised:
            require_admin(self.user)
        self.assertEqual(raised.exception.status_code, 403)

        self.user.role = "manager"
        self.assertIs(require_manager_or_admin(self.user), self.user)
        with self.assertRaises(HTTPException):
            require_admin(self.user)

        self.user.role = "admin"
        self.assertIs(require_manager_or_admin(self.user), self.user)
        self.assertIs(require_admin(self.user), self.user)

    def test_rate_limit_is_attached_to_sensitive_auth_routes(self) -> None:
        for path in (
            "/auth/login",
            "/auth/forgot-password",
            "/auth/reset-password",
        ):
            with self.subTest(path=path):
                route = next(
                    route
                    for route in auth_router.routes
                    if getattr(route, "path", None) == path
                )
                self.assertTrue(
                    any(
                        getattr(dependency.call, "__name__", "")
                        == "check"
                        for dependency in route.dependant.dependencies
                    )
                )

    def test_redis_rate_limit_store_uses_atomic_server_script(self) -> None:
        class FakeRedis:
            def __init__(self) -> None:
                self.call = None

            def eval(self, script, numkeys, key, window):
                self.call = (script, numkeys, key, window)
                return [3, 42]

        client = FakeRedis()
        count, retry_after = RedisRateLimitStore(client).consume(
            "rate-limit:test",
            60,
        )

        self.assertEqual((count, retry_after), (3, 42))
        self.assertEqual(client.call[1:], (1, "rate-limit:test", 60))
        self.assertIn("redis.call", client.call[0])

    def test_rate_limit_enforces_configured_count(self) -> None:
        store = rate_limit_module.InMemoryRateLimitStore()
        request = Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/auth/login",
                "raw_path": b"/auth/login",
                "query_string": b"",
                "headers": [],
                "client": ("192.0.2.42", 1234),
                "server": ("testserver", 80),
            }
        )
        dependency = rate_limit_module.rate_limit("test-login", 2, 60)

        with patch.object(rate_limit_module, "_get_store", return_value=store):
            dependency(request)
            dependency(request)
            with self.assertRaises(HTTPException) as raised:
                dependency(request)

        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn("Retry-After", raised.exception.headers)

    def test_login_http_returns_429_at_configured_request_limit(self) -> None:
        original_limit = settings.LOGIN_RATE_LIMIT_REQUESTS
        original_window = settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
        original_overrides = app.dependency_overrides.copy()
        settings.LOGIN_RATE_LIMIT_REQUESTS = 2
        settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60
        app.dependency_overrides[get_db] = lambda: self.db
        store = rate_limit_module.InMemoryRateLimitStore()
        try:
            with (
                patch.object(
                    rate_limit_module,
                    "_get_store",
                    return_value=store,
                )
            ):
                responses = [
                    self.post_form(
                        "/auth/login",
                        {
                            "username": "missing@example.test",
                            "password": "not-a-real-password",
                        },
                    )
                    for _ in range(3)
                ]
        finally:
            settings.LOGIN_RATE_LIMIT_REQUESTS = original_limit
            settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS = original_window
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

        self.assertEqual(responses[0][0], 401)
        self.assertEqual(responses[1][0], 401)
        self.assertEqual(responses[2][0], 429)
        self.assertIn(b"retry-after", responses[2][1])

    def test_password_reset_routes_http_return_429_at_configured_limits(
        self,
    ) -> None:
        route_cases = (
            (
                "/auth/forgot-password",
                {"email": "unknown@example.com"},
                "FORGOT_PASSWORD_RATE_LIMIT_REQUESTS",
                "FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS",
                200,
            ),
            (
                "/auth/reset-password",
                {
                    "token": "x" * 32,
                    "new_password": "a sufficiently long password",
                },
                "RESET_PASSWORD_RATE_LIMIT_REQUESTS",
                "RESET_PASSWORD_RATE_LIMIT_WINDOW_SECONDS",
                400,
            ),
        )
        original_overrides = app.dependency_overrides.copy()
        original_settings = {
            name: getattr(settings, name)
            for case in route_cases
            for name in case[2:4]
        }
        app.dependency_overrides[get_db] = lambda: self.db

        try:
            with patch.object(
                rate_limit_module,
                "_get_store",
                return_value=rate_limit_module.InMemoryRateLimitStore(),
            ):
                for (
                    path,
                    payload,
                    limit_name,
                    window_name,
                    first_status,
                ) in route_cases:
                    with self.subTest(path=path):
                        setattr(settings, limit_name, 1)
                        setattr(settings, window_name, 60)
                        body = json.dumps(payload).encode("utf-8")
                        headers = [
                            (b"content-type", b"application/json"),
                        ]
                        first = self.asgi_request(
                            "POST",
                            path,
                            body,
                            headers,
                        )
                        second = self.asgi_request(
                            "POST",
                            path,
                            body,
                            headers,
                        )
                        self.assertEqual(first[0], first_status)
                        self.assertEqual(second[0], 429)
                        self.assertIn(b"retry-after", second[1])
        finally:
            for name, value in original_settings.items():
                setattr(settings, name, value)
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

    def test_production_rate_limit_requires_shared_redis(self) -> None:
        request = Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "POST",
                "scheme": "http",
                "path": "/auth/login",
                "raw_path": b"/auth/login",
                "query_string": b"",
                "headers": [],
                "client": ("192.0.2.43", 1234),
                "server": ("testserver", 80),
            }
        )
        with (
            patch.object(settings, "APP_ENV", "production"),
            patch.object(settings, "RATE_LIMIT_REDIS_URL", None),
        ):
            with self.assertRaises(HTTPException) as raised:
                rate_limit_module.rate_limit("test-production", 1, 60)(
                    request
                )
        self.assertEqual(raised.exception.status_code, 503)

    def test_cors_origins_are_explicit_and_wildcard_is_rejected(self) -> None:
        local = Settings(
            DATABASE_URL="sqlite://",
            SECRET_KEY="test-only-key",
        )
        self.assertEqual(
            local.cors_allowed_origins,
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        )
        configured = Settings(
            DATABASE_URL="sqlite://",
            SECRET_KEY="test-only-key",
            CORS_ALLOWED_ORIGINS=(
                "https://workflow.example, http://localhost:5173"
            ),
        )
        self.assertEqual(
            configured.cors_allowed_origins,
            ["https://workflow.example", "http://localhost:5173"],
        )
        with self.assertRaises(ValueError):
            Settings(
                DATABASE_URL="sqlite://",
                SECRET_KEY="test-only-key",
                CORS_ALLOWED_ORIGINS="*",
            )

    def test_production_requires_explicit_cors_and_redis_configuration(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            Settings(
                DATABASE_URL="sqlite://",
                SECRET_KEY="test-only-key",
                APP_ENV="production",
                CORS_ALLOWED_ORIGINS="https://workflow.example",
            )

        configured = Settings(
            DATABASE_URL="sqlite://",
            SECRET_KEY="test-only-key",
            APP_ENV="production",
            CORS_ALLOWED_ORIGINS="https://workflow.example",
            RATE_LIMIT_REDIS_URL="redis://localhost:6379/0",
            REFRESH_COOKIE_SECURE=True,
        )
        self.assertEqual(
            configured.cors_allowed_origins,
            ["https://workflow.example"],
        )

    def test_production_rejects_insecure_refresh_cookie_configuration(self):
        with self.assertRaises(ValueError):
            Settings(
                DATABASE_URL="sqlite://",
                SECRET_KEY="test-only-key",
                APP_ENV="production",
                CORS_ALLOWED_ORIGINS="https://workflow.example",
                RATE_LIMIT_REDIS_URL="redis://localhost:6379/0",
            )

    def test_samesite_none_requires_secure_refresh_cookie(self):
        with self.assertRaises(ValueError):
            Settings(
                DATABASE_URL="sqlite://",
                SECRET_KEY="test-only-key",
                REFRESH_COOKIE_SAMESITE="none",
            )

    def test_app_cors_middleware_uses_configured_origins(self) -> None:
        from starlette.middleware.cors import CORSMiddleware

        cors_middleware = next(
            middleware
            for middleware in app.user_middleware
            if middleware.cls is CORSMiddleware
        )
        self.assertEqual(
            cors_middleware.kwargs["allow_origins"],
            settings.cors_allowed_origins,
        )

    def test_cors_http_response_trusts_configured_origins_only(self) -> None:
        allowed_origin = settings.cors_allowed_origins[0]
        allowed_status, allowed_headers, _ = self.asgi_request(
            "GET",
            "/health",
            headers=[(b"origin", allowed_origin.encode("ascii"))],
        )
        denied_status, denied_headers, _ = self.asgi_request(
            "GET",
            "/health",
            headers=[(b"origin", b"https://untrusted.example")],
        )

        self.assertEqual(allowed_status, 200)
        self.assertEqual(
            allowed_headers.get(b"access-control-allow-origin"),
            allowed_origin.encode("ascii"),
        )
        self.assertEqual(denied_status, 200)
        self.assertNotIn(b"access-control-allow-origin", denied_headers)

    def test_task_list_filters_sorts_paginates_and_preserves_visibility(
        self,
    ) -> None:
        visible_tasks = [
            Task(
                title=f"Task {index}",
                status="todo" if index < 2 else "done",
                priority="high" if index == 2 else "medium",
                created_by=self.user.id,
                assigned_to=self.user.id,
            )
            for index in range(3)
        ]
        hidden_task = Task(
            title="Other user's task",
            status="done",
            priority="high",
            created_by=self.user.id + 100,
            assigned_to=self.user.id + 100,
        )
        self.db.add_all([*visible_tasks, hidden_task])
        self.db.commit()

        results = get_tasks(
            status="done",
            priority="high",
            assigned_to=None,
            skip=0,
            limit=1,
            sort_by="title",
            sort_order="asc",
            current_user=self.user,
            db=self.db,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Task 2")
        self.assertEqual(results[0].assigned_to, self.user.id)

    def test_user_list_filters_sorts_and_paginates(self) -> None:
        users = [
            User(
                name=f"Member {index}",
                email=f"member-{index}-{time.time_ns()}@example.com",
                hashed_password="not-a-real-hash",
                role="manager" if index == 1 else "employee",
                is_active=index != 2,
            )
            for index in range(3)
        ]
        self.db.add_all(users)
        self.db.commit()
        admin = User(
            name="Admin",
            email=f"admin-{time.time_ns()}@example.com",
            hashed_password="not-a-real-hash",
            role="admin",
            is_active=True,
        )

        results = get_users(
            skip=0,
            limit=1,
            role="manager",
            is_active=True,
            search="Member",
            sort_by="name",
            sort_order="asc",
            current_user=admin,
            db=self.db,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].role, "manager")
        self.assertEqual(results[0].name, "Member 1")

    def test_document_list_filters_sorts_and_paginates(self) -> None:
        task = Task(
            title="Document list task",
            status="todo",
            priority="medium",
            created_by=self.user.id,
            assigned_to=self.user.id,
        )
        self.db.add(task)
        self.db.flush()
        documents = [
            Document(
                file_name=f"report-{index}.pdf",
                file_path=f"uploads/{index}.pdf",
                version=index + 1,
                uploaded_by=self.user.id,
                task_id=task.id,
            )
            for index in range(3)
        ]
        self.db.add_all(documents)
        self.db.commit()

        results = get_task_documents(
            task_id=task.id,
            skip=0,
            limit=1,
            file_name="report",
            sort_by="version",
            sort_order="desc",
            current_user=self.user,
            db=self.db,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].version, 3)
        self.assertEqual(results[0].task_id, task.id)

    def test_approval_and_history_lists_are_filtered_and_paginated(self) -> None:
        task = Task(
            title="Approval list task",
            status="review",
            priority="medium",
            created_by=self.user.id,
            assigned_to=self.user.id,
        )
        self.db.add(task)
        self.db.flush()
        approvals = [
            Approval(
                task_id=task.id,
                requested_by=self.user.id,
                approver_id=self.user.id,
                level="manager",
                status=status_value,
            )
            for status_value in ("pending", "approved", "pending")
        ]
        self.db.add_all(approvals)
        self.db.flush()
        histories = [
            ApprovalHistory(
                approval_id=approval.id,
                task_id=task.id,
                action_by=self.user.id,
                action=("submitted", "approved", "rejected")[index],
            )
            for index, approval in enumerate(approvals)
        ]
        self.db.add_all(histories)
        self.db.commit()

        approval_page = get_task_approvals(
            task_id=task.id,
            skip=0,
            limit=1,
            approval_status="pending",
            sort_by="status",
            sort_order="desc",
            db=self.db,
            current_user=self.user,
        )
        history_page = get_approval_history(
            task_id=task.id,
            skip=0,
            limit=2,
            action="approved",
            sort_by="action",
            sort_order="desc",
            db=self.db,
            current_user=self.user,
        )

        self.assertEqual(len(approval_page), 1)
        self.assertEqual(approval_page[0].status, "pending")
        self.assertEqual(len(history_page), 1)
        self.assertEqual(history_page[0].action, "approved")

    def test_notifications_list_is_user_scoped_filtered_and_paginated(
        self,
    ) -> None:
        other_user = User(
            name="Other user",
            email=f"other-{time.time_ns()}@example.com",
            hashed_password="not-a-real-hash",
            role="employee",
            is_active=True,
        )
        self.db.add(other_user)
        self.db.flush()
        self.db.add_all(
            [
                Notification(
                    user_id=self.user.id,
                    message=f"Unread {index}",
                    is_read=False,
                )
                for index in range(2)
            ]
            + [
                Notification(
                    user_id=self.user.id,
                    message="Read",
                    is_read=True,
                ),
                Notification(
                    user_id=other_user.id,
                    message="Not visible",
                    is_read=False,
                ),
            ]
        )
        self.db.commit()

        results = get_notifications(
            unread_only=True,
            skip=0,
            limit=1,
            sort_by="id",
            sort_order="desc",
            db=self.db,
            current_user=self.user,
        )

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].is_read)
        self.assertEqual(results[0].user_id, self.user.id)

    def test_audit_log_list_filters_sorts_and_paginates(self) -> None:
        self.db.add_all(
            [
                AuditLog(
                    user_id=self.user.id,
                    action=f"TASK_ACTION_{index}",
                    entity="task",
                    entity_id=index,
                )
                for index in range(3)
            ]
        )
        self.db.commit()
        admin = User(
            name="Audit Admin",
            email=f"audit-admin-{time.time_ns()}@example.com",
            hashed_password="not-a-real-hash",
            role="admin",
            is_active=True,
        )

        results = get_audit_logs(
            skip=0,
            limit=1,
            action="TASK_ACTION_1",
            entity="task",
            user_id=self.user.id,
            start_date=None,
            end_date=None,
            sort_by="timestamp",
            sort_order="desc",
            db=self.db,
            current_user=admin,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].action, "TASK_ACTION_1")

    def test_task_query_pagination_and_filter_values_are_validated_http_422(
        self,
    ) -> None:
        original_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_current_user] = lambda: self.user
        try:
            invalid_limit = self.asgi_request(
                "GET",
                "/tasks/",
                query_string=b"limit=101",
            )
            invalid_status = self.asgi_request(
                "GET",
                "/tasks/",
                query_string=b"status=not-a-status",
            )
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(original_overrides)

        self.assertEqual(invalid_limit[0], 422)
        self.assertEqual(invalid_status[0], 422)

if __name__ == "__main__":
    unittest.main()
