from __future__ import annotations

import pytest

from src.domain.entities.report import Report, ReportStatus, ReportType
from src.domain.entities.tenant import Tenant, TenantPlan, TenantStatus
from src.domain.entities.user import User, UserRole, UserStatus
from src.domain.value_objects.email import Email


class TestUser:
    def test_new_user_is_pending(self):
        user = User(email="a@b.com", name="Ana", hashed_password="x", role=UserRole.CONTADOR)
        assert user.status == UserStatus.PENDING

    def test_activate_sets_active(self):
        user = User(email="a@b.com", name="Ana", hashed_password="x", role=UserRole.CONTADOR)
        user.activate()
        assert user.is_active()

    def test_deactivate_sets_inactive(self):
        user = User(email="a@b.com", name="Ana", hashed_password="x", role=UserRole.CONTADOR)
        user.activate()
        user.deactivate()
        assert not user.is_active()

    def test_admin_can_manage_any_tenant(self):
        import uuid
        admin = User(email="admin@b.com", name="Admin", hashed_password="x", role=UserRole.ADMIN)
        assert admin.can_manage_tenant(uuid.uuid4())

    def test_contador_can_manage_own_tenant(self):
        import uuid
        tid = uuid.uuid4()
        contador = User(
            email="c@b.com", name="C", hashed_password="x",
            role=UserRole.CONTADOR, tenant_id=tid,
        )
        assert contador.can_manage_tenant(tid)
        assert not contador.can_manage_tenant(uuid.uuid4())


class TestTenant:
    def test_slug_generated_from_name(self):
        t = Tenant(name="Mi Empresa", owner_email="o@e.com")
        assert t.slug == "mi-empresa"

    def test_upgrade_changes_plan_and_limit(self):
        t = Tenant(name="T", owner_email="o@e.com")
        t.upgrade(TenantPlan.PROFESSIONAL)
        assert t.plan == TenantPlan.PROFESSIONAL
        assert t.max_clients == 50

    def test_suspend_changes_status(self):
        t = Tenant(name="T", owner_email="o@e.com")
        t.suspend()
        assert t.status == TenantStatus.SUSPENDED
        assert not t.is_active()


class TestReport:
    def _make_report(self) -> Report:
        import uuid
        return Report(
            tenant_id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            created_by=uuid.uuid4(),
            report_type=ReportType.SAZON,
            period="2026-01",
        )

    def test_new_report_is_pending(self):
        r = self._make_report()
        assert r.status == ReportStatus.PENDING

    def test_lifecycle(self):
        r = self._make_report()
        r.mark_processing()
        assert r.status == ReportStatus.PROCESSING
        r.mark_completed()
        assert r.status == ReportStatus.COMPLETED

    def test_mark_failed_stores_error(self):
        r = self._make_report()
        r.mark_failed("Missing column")
        assert r.status == ReportStatus.FAILED
        assert "Missing column" in (r.error_message or "")

    def test_add_source_file(self):
        r = self._make_report()
        f = r.add_source_file("sales", "tenant/client/sales.xlsx", "ventas.xlsx")
        assert len(r.source_files) == 1
        assert f.original_name == "ventas.xlsx"


class TestEmail:
    def test_valid_email(self):
        e = Email("user@example.com")
        assert e.domain == "example.com"

    def test_invalid_email_raises(self):
        with pytest.raises(ValueError):
            Email("not-an-email")
