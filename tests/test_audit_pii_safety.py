from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.admin import AdminUserAdmin
from apps.accounts.models import AdminRole, AdminUser
from apps.audit.admin import AuditedModelAdmin
from apps.audit.models import OperationLog
from apps.students.models import DevelopmentStage, PartyBranch, Student


PII_MARKERS = ("敏感姓名甲", "PII20260001", "pii-admin@example.invalid", "含姓名的文件.xlsx")


class AuditPiiSafetyTests(TestCase):
    def setUp(self) -> None:
        self.operator = AdminUser.objects.create_superuser(
            username="audit-operator",
            password="testpass123",
            email="operator@example.invalid",
            role=AdminRole.DATA_ADMIN,
        )
        self.branch = PartyBranch.objects.create(code="PII", name="合成测试支部")
        self.student = Student.objects.create(
            name=PII_MARKERS[0],
            student_number=PII_MARKERS[1],
            branch=self.branch,
            development_stage=DevelopmentStage.ACTIVIST,
        )

    def assert_log_has_no_pii(self, log: OperationLog) -> None:
        serialized = "|".join(
            (log.operator_role, log.action, log.target_type, log.target_id, log.description)
        )
        for marker in PII_MARKERS:
            self.assertNotIn(marker, serialized)

    def test_student_login_audit_uses_internal_id_only(self) -> None:
        response = self.client.post(
            reverse("accounts:student_login"),
            {"name": self.student.name, "student_number": self.student.student_number},
        )
        self.assertEqual(response.status_code, 302)
        log = OperationLog.objects.get(action="student_login_success")
        self.assertEqual(log.target_id, str(self.student.pk))
        self.assertIsNone(log.operator)
        self.assert_log_has_no_pii(log)

    def test_admin_detail_audit_description_has_no_student_pii(self) -> None:
        self.client.force_login(self.operator)
        response = self.client.get(
            reverse("students:admin_student_detail", kwargs={"pk": self.student.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assert_log_has_no_pii(OperationLog.objects.get(action="view_student_detail"))

    def test_admin_data_change_audit_uses_model_and_internal_id(self) -> None:
        request = RequestFactory().post("/admin/students/student/1/change/")
        request.user = self.operator
        model_admin = AuditedModelAdmin(Student, admin.site)

        model_admin.log_change(request, self.student, "changed")

        log = OperationLog.objects.get(action="record_updated")
        self.assertEqual(log.target_id, str(self.student.pk))
        self.assert_log_has_no_pii(log)
        self.assertFalse(LogEntry.objects.exists())

    def test_role_change_audit_does_not_store_email(self) -> None:
        target = AdminUser.objects.create_user(
            username="role-target",
            password="testpass123",
            email=PII_MARKERS[2],
            role=AdminRole.VIEWER_ADMIN,
        )
        request = RequestFactory().post("/admin/accounts/adminuser/1/change/")
        request.user = self.operator
        target.role = AdminRole.DATA_ADMIN

        AdminUserAdmin(AdminUser, admin.site).save_model(request, target, form=None, change=True)

        log = OperationLog.objects.get(action="admin_role_changed")
        self.assertEqual(log.target_id, str(target.pk))
        self.assert_log_has_no_pii(log)

    def test_all_application_audit_descriptions_are_static_and_pii_free(self) -> None:
        OperationLog.objects.create(
            operator=self.operator,
            operator_role=self.operator.role,
            action="upload_excel",
            target_type="ImportBatch",
            target_id="9",
            description="上传Excel并生成服务端预览",
        )
        for log in OperationLog.objects.all():
            self.assert_log_has_no_pii(log)
