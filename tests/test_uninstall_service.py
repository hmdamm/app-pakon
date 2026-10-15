"""Unit tests for the uninstallation service."""

from appharbor.domain.models import (
    InstallationRecord,
    ScopeEnum,
    SourceEnum,
)
from appharbor.inventory.orchestrator import InventoryOrchestrator
from appharbor.uninstall.service import UninstallService


def test_uninstall_service_blocks_critical_package():
    orch = InventoryOrchestrator(providers=[])
    service = UninstallService(orch)

    rec = InstallationRecord(
        id="rpm:sys:glibc",
        name="GNU C Library",
        package_id="glibc",
        source=SourceEnum.RPM,
        scope=ScopeEnum.SYSTEM,
        is_critical_system_package=True,
    )

    plan = service.create_uninstall_plan(rec)
    assert plan.is_executable is False
    assert plan.is_critical_warning is True
    assert "critical" in plan.error_message.lower()

    # Execution should fail immediately
    res = service.execute_plan(plan)
    assert res.success is False
    assert "blocked" in res.message.lower()
