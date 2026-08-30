from __future__ import annotations

import hashlib
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from config.settings import BASE_DIR


BOOTSTRAP_ROOT = BASE_DIR / "static/vendor/bootstrap/5.3.3"
BOOTSTRAP_SHA256 = {
    "css/bootstrap.min.css": "3c8f27e6009ccfd710a905e6dcf12d0ee3c6f2ac7da05b0572d3e0d12e736fc8",
    "css/bootstrap.min.css.map": "f12338536350a422c64d02d6e43ff1dea493c3156ad823fe19761cdd5d56c05b",
    "js/bootstrap.bundle.min.js": "0833b2e9c3a26c258476c46266e6877fc75218625162e0460be9a3a098a61c6c",
    "js/bootstrap.bundle.min.js.map": "5e3e0763164143baaa1ca0706b6100ba0452f911d6ce9713b48e3dbe07b35125",
    "LICENSE": "8c14611ae41ac6fd543c13349f22188eb12c69b3e59105c5eca3925a8e4eca3e",
}
EXTERNAL_RUNTIME_ASSET = re.compile(
    r"<(?:link|script)\b[^>]*(?:href|src)=[\"']https?://",
    flags=re.IGNORECASE,
)


class LocalStaticAssetContractTests(SimpleTestCase):
    def test_bootstrap_vendor_files_match_frozen_release(self) -> None:
        for relative_path, expected_sha256 in BOOTSTRAP_SHA256.items():
            with self.subTest(relative_path=relative_path):
                asset = BOOTSTRAP_ROOT / relative_path
                self.assertTrue(asset.is_file())
                self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), expected_sha256)

    def test_bootstrap_license_is_retained(self) -> None:
        license_text = (BOOTSTRAP_ROOT / "LICENSE").read_text(encoding="utf-8")

        self.assertIn("The MIT License (MIT)", license_text)
        self.assertIn("Bootstrap Authors", license_text)

    def test_runtime_templates_do_not_load_external_css_or_javascript(self) -> None:
        violations: list[str] = []
        for template in (BASE_DIR / "templates").rglob("*.html"):
            if EXTERNAL_RUNTIME_ASSET.search(template.read_text(encoding="utf-8")):
                violations.append(template.relative_to(BASE_DIR).as_posix())

        self.assertEqual(violations, [])

    def test_home_page_references_local_bootstrap_assets(self) -> None:
        response = self.client.get(reverse("home"))

        self.assertContains(response, "/static/vendor/bootstrap/5.3.3/css/bootstrap.min.css")
        self.assertContains(response, "/static/vendor/bootstrap/5.3.3/js/bootstrap.bundle.min.js")
        self.assertNotContains(response, "cdn.jsdelivr.net")

    def test_collectstatic_copies_frozen_vendor_assets(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            static_root = Path(temporary_directory)
            with override_settings(STATIC_ROOT=static_root):
                call_command("collectstatic", interactive=False, verbosity=0)

            for relative_path in BOOTSTRAP_SHA256:
                with self.subTest(relative_path=relative_path):
                    self.assertTrue((static_root / f"vendor/bootstrap/5.3.3/{relative_path}").is_file())
