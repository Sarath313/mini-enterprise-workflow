import unittest

from unittest.mock import MagicMock, patch

from app.core.password_reset_delivery import deliver_password_reset_token
from app.database import settings


class PasswordResetDeliveryTests(unittest.TestCase):
    def test_smtp_delivery_sends_reset_link_with_starttls(self) -> None:
        smtp = MagicMock()
        smtp_context = MagicMock()
        smtp_context.__enter__.return_value = smtp
        with (
            patch.object(settings, "PASSWORD_RESET_DELIVERY_MODE", "smtp"),
            patch.object(settings, "SMTP_HOST", "smtp.example.test"),
            patch.object(settings, "SMTP_PORT", 587),
            patch.object(settings, "SMTP_USERNAME", "workflow"),
            patch.object(settings, "SMTP_PASSWORD", "test-only-password"),
            patch.object(settings, "SMTP_FROM_EMAIL", "noreply@example.test"),
            patch.object(
                settings,
                "PASSWORD_RESET_FRONTEND_URL",
                "https://workflow.example/",
            ),
            patch.object(settings, "SMTP_STARTTLS", True),
            patch(
                "app.core.password_reset_delivery.smtplib.SMTP",
                return_value=smtp_context,
            ) as smtp_factory,
        ):
            deliver_password_reset_token(
                "member@example.test",
                "opaque-reset-token",
            )

        smtp_factory.assert_called_once_with(
            "smtp.example.test",
            587,
            timeout=10,
        )
        smtp.starttls.assert_called_once_with()
        smtp.login.assert_called_once_with(
            "workflow",
            "test-only-password",
        )
        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message["To"], "member@example.test")
        self.assertIn(
            "https://workflow.example/reset-password"
            "#token=opaque-reset-token",
            message.get_content(),
        )

    def test_incomplete_smtp_configuration_sends_nothing(self) -> None:
        with (
            patch.object(settings, "PASSWORD_RESET_DELIVERY_MODE", "smtp"),
            patch.object(settings, "SMTP_HOST", None),
            patch(
                "app.core.password_reset_delivery.smtplib.SMTP"
            ) as smtp_factory,
        ):
            deliver_password_reset_token(
                "member@example.test",
                "opaque-reset-token",
            )

        smtp_factory.assert_not_called()

    def test_smtp_failure_does_not_propagate_or_log_token(self) -> None:
        with (
            patch.object(settings, "PASSWORD_RESET_DELIVERY_MODE", "smtp"),
            patch.object(settings, "SMTP_HOST", "smtp.example.test"),
            patch.object(settings, "SMTP_FROM_EMAIL", "noreply@example.test"),
            patch.object(
                settings,
                "PASSWORD_RESET_FRONTEND_URL",
                "https://workflow.example",
            ),
            patch.object(settings, "SMTP_USERNAME", None),
            patch.object(settings, "SMTP_PASSWORD", None),
            patch.object(settings, "SMTP_STARTTLS", False),
            patch(
                "app.core.password_reset_delivery.smtplib.SMTP",
                side_effect=OSError("network unavailable"),
            ),
            self.assertLogs(
                "app.core.password_reset_delivery",
                level="ERROR",
            ) as captured,
        ):
            deliver_password_reset_token(
                "member@example.test",
                "never-log-this-token",
            )

        self.assertIn("OSError", captured.output[0])
        self.assertNotIn("never-log-this-token", captured.output[0])

    def test_disabled_mode_does_not_open_smtp_connection(self) -> None:
        with (
            patch.object(settings, "PASSWORD_RESET_DELIVERY_MODE", "disabled"),
            patch(
                "app.core.password_reset_delivery.smtplib.SMTP"
            ) as smtp_factory,
        ):
            deliver_password_reset_token(
                "member@example.test",
                "opaque-reset-token",
            )

        smtp_factory.assert_not_called()
