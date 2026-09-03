from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from django.db import DatabaseError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from config.settings import BASE_DIR


class LivenessTests(TestCase):
    def test_liveness_is_process_only_and_small(self) -> None:
        with patch("config.views.connection.cursor") as cursor:
            response = self.client.get(reverse("liveness"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok\n")
        self.assertEqual(response["Content-Type"], "text/plain")
        cursor.assert_not_called()


class ReadinessTests(TestCase):
    def test_readiness_checks_database_without_exposing_details(self) -> None:
        response = self.client.get(reverse("readiness"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok\n")

    @patch("config.views.connection.cursor", side_effect=DatabaseError("secret path"))
    def test_readiness_failure_is_generic(self, _cursor: object) -> None:
        response = self.client.get(reverse("readiness"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.content, b"unavailable\n")
        self.assertNotContains(response, "secret path", status_code=503)


class ObservabilityContractTests(SimpleTestCase):
    def test_compose_rotates_service_logs_and_uses_application_readiness(self) -> None:
        compose = (BASE_DIR / "compose.production.yml").read_text(encoding="utf-8")

        self.assertEqual(compose.count("driver: local"), 2)
        self.assertEqual(compose.count('max-size: "20m"'), 2)
        self.assertEqual(compose.count('max-file: "5"'), 2)
        self.assertIn("/health/ready/", compose)

    def test_monitoring_assets_exist_and_do_not_embed_secrets(self) -> None:
        expected = [
            "scripts/check_production_health.sh",
            "deploy/systemd/party-archive-health.service",
            "deploy/systemd/party-archive-health.timer",
        ]
        for relative_path in expected:
            with self.subTest(relative_path=relative_path):
                content = (BASE_DIR / relative_path).read_text(encoding="utf-8")
                self.assertNotIn("password=", content.lower())
                self.assertNotIn("secret_key=", content.lower())

    def test_monitor_checks_required_operational_signals(self) -> None:
        script = (BASE_DIR / "scripts/check_production_health.sh").read_text(
            encoding="utf-8"
        )

        for signal in ("docker inspect", "df -P", "openssl x509", "BACKUP_SUCCESS_FILE", "timedatectl"):
            with self.subTest(signal=signal):
                self.assertIn(signal, script)
