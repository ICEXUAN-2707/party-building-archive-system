from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_HTTP_DOCS = (
    "docs/deployment_guide.md",
    "docs/operations_runbook.md",
    "docs/release_checklist.md",
    "docs/incident_response.md",
    "docs/container_ci.md",
)


class OperationsDocumentationContractTests(TestCase):
    def read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_deployment_guide_covers_immutable_release_and_safe_compose(self):
        guide = self.read("docs/deployment_guide.md")
        for required in (
            "不可变",
            "validate_production_host.sh",
            "initialize_production_host.sh",
            "config --quiet",
            "initialize_branches",
            "createsuperuser",
            "down --volumes",
            "不得导入真实数据",
            "<FIXED_PUBLIC_IPV4>",
        ):
            self.assertIn(required, guide)

    def test_operations_runbook_covers_upgrade_rollback_and_restore(self):
        runbook = self.read("docs/operations_runbook.md")
        for required in (
            "日常升级",
            "应用回退",
            "暂停",
            "SHA-256",
            "migrate --check",
            "RPO",
            "RTO",
            "0600",
        ):
            self.assertIn(required, runbook)

    def test_release_checklist_preserves_go_no_go_gates(self):
        checklist = self.read("docs/release_checklist.md")
        for required in (
            "RC Tag",
            "容器CI",
            "P0/P1",
            "COS",
            "真实数据授权",
            "Go签字",
            "阻断",
        ):
            self.assertIn(required, checklist)

    def test_incident_guide_covers_required_incidents_and_prohibitions(self):
        guide = self.read("docs/incident_response.md")
        for required in (
            "502/503",
            "磁盘不足",
            "HTTP入口暴露范围异常",
            "备份过期",
            "SQLite损坏",
            "安全或隐私事件",
            "禁止",
        ):
            self.assertIn(required, guide)

    def test_active_deployment_docs_use_fixed_ip_http_contract(self):
        combined = "\n".join(self.read(path) for path in ACTIVE_HTTP_DOCS)
        for required in ("固定公网 IPv4", "HTTP", "80", "8000"):
            self.assertIn(required, combined)
        for forbidden in (
            "HTTP跳转HTTPS",
            "HTTP 跳转 HTTPS",
            "受信任 TLS 证书",
            "正式域名",
            "TLS剩余",
            "TLS 剩余",
        ):
            self.assertNotIn(forbidden, combined)

    def test_host_validator_is_read_only_and_checks_baseline(self):
        validator = self.read("scripts/validate_production_host.sh")
        for required in (
            "x86_64",
            "24.04",
            "docker compose version",
            "NTPSynchronized",
            "failures=",
        ):
            self.assertIn(required, validator)
        for forbidden in (
            "apt install",
            "apt-get install",
            "ufw ",
            "chmod ",
            "chown ",
            "systemctl enable",
        ):
            self.assertNotIn(forbidden, validator)

    def test_no_real_asset_values_are_committed(self):
        combined = "\n".join(self.read(path) for path in ACTIVE_HTTP_DOCS)
        self.assertNotIn("SECRET_KEY=", combined)
        self.assertNotRegex(combined, r"AKID[A-Za-z0-9]{12,}")
