from django.test import SimpleTestCase

from config.settings import BASE_DIR


class ProductionComposeContractTests(SimpleTestCase):
    def setUp(self) -> None:
        self.compose = (BASE_DIR / "compose.production.yml").read_text(encoding="utf-8")

    def test_web_is_internal_non_root_image_with_persistent_paths(self) -> None:
        self.assertIn("WEB_IMAGE must reference a reviewed immutable release image", self.compose)
        self.assertIn('expose:\n      - "8000"', self.compose)
        self.assertNotIn("8000:8000", self.compose)
        self.assertIn("frontend:", self.compose)
        self.assertIn("internal: true", self.compose)
        self.assertIn("no-new-privileges:true", self.compose)
        for path in ("database", "media", "static", "backups"):
            self.assertIn(f"/data/{path}", self.compose)
        self.assertEqual(self.compose.count("create_host_path: false"), 5)

    def test_compose_requires_external_secrets_and_only_publishes_http(self) -> None:
        self.assertIn("PRODUCTION_ENV_FILE", self.compose)
        self.assertNotIn("TLS_CERT_DIR", self.compose)
        self.assertIn("NGINX_SERVER_NAME must be the reviewed fixed public IPv4 address", self.compose)
        self.assertNotIn("DJANGO_SECRET_KEY=", self.compose)
        self.assertNotIn("privkey.pem:", self.compose)
        self.assertIn('"${HTTP_BIND_ADDRESS:-0.0.0.0}:${HTTP_PORT:-80}:80"', self.compose)
        self.assertNotIn("HTTPS_PORT", self.compose)
        self.assertNotIn(":443", self.compose)

    def test_runtime_limits_match_two_core_four_gib_host(self) -> None:
        self.assertIn("mem_limit: 2g", self.compose)
        self.assertIn("cpus: 1.5", self.compose)
        self.assertIn("mem_limit: 256m", self.compose)
        self.assertIn("cpus: 0.5", self.compose)
        self.assertIn("stop_grace_period: 40s", self.compose)


class ProductionNginxContractTests(SimpleTestCase):
    def setUp(self) -> None:
        self.nginx = (BASE_DIR / "deploy/nginx/nginx.conf").read_text(encoding="utf-8")
        self.site = (BASE_DIR / "deploy/nginx/templates/party-archive.conf.template").read_text(
            encoding="utf-8"
        )

    def test_http_proxy_and_static_contract(self) -> None:
        self.assertIn("server_name ${NGINX_SERVER_NAME};", self.site)
        self.assertIn("listen 80 default_server;", self.site)
        self.assertNotIn("listen 443", self.site)
        self.assertNotIn("ssl_certificate", self.site)
        self.assertIn("proxy_pass http://party_archive_web;", self.site)
        self.assertIn("proxy_set_header X-Forwarded-Proto http;", self.site)
        self.assertIn("location /static/", self.site)
        self.assertNotIn("location /media/", self.site)

    def test_access_log_does_not_record_query_string(self) -> None:
        log_format = self.nginx.split("access_log", 1)[0]
        self.assertIn("$request_method $uri $server_protocol", log_format)
        self.assertNotIn("$request_uri", log_format)
        self.assertNotIn("$args", log_format)

    def test_tls_private_key_is_neither_referenced_nor_committed(self) -> None:
        self.assertNotIn("/etc/nginx/tls/privkey.pem", self.site)
        self.assertFalse((BASE_DIR / "deploy/nginx/tls/privkey.pem").exists())


class ProductionHostInitializationContractTests(SimpleTestCase):
    def test_initializer_is_fixed_scope_and_non_destructive(self) -> None:
        script = (BASE_DIR / "scripts/initialize_production_host.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('readonly ROOT="/srv/party-archive"', script)
        self.assertIn('readonly APP_UID="10001"', script)
        self.assertIn("install -d", script)
        self.assertNotIn("rm -", script)
        self.assertNotIn("chmod -R", script)
