"""Safe uninstallation service coordinating plans, safety checks, and execution."""

from __future__ import annotations

import logging
from typing import Callable, Optional, TYPE_CHECKING

from appharbor.domain.models import (
    InstallationRecord,
    OperationResult,
    UninstallPlan,
)
if TYPE_CHECKING:
    from appharbor.inventory.orchestrator import InventoryOrchestrator
from appharbor.uninstall.guards import is_critical_package

logger = logging.getLogger(__name__)


class UninstallService:
    """Coordinates safe, explicit uninstallation workflows."""

    def __init__(self, orchestrator: InventoryOrchestrator):
        self._orchestrator = orchestrator

    def create_uninstall_plan(
        self,
        record: InstallationRecord,
        keep_data: bool = True,
    ) -> UninstallPlan:
        """Create a transparent, verified uninstallation plan before user confirmation."""
        # 1. Critical package safety guard
        if record.is_critical_system_package or is_critical_package(record.package_id):
            return UninstallPlan(
                record=record,
                target_summary=f"Critical system component: {record.name} ({record.package_id})",
                commands_to_run=[],
                requires_elevation=True,
                is_critical_warning=True,
                is_executable=False,
                error_message=(
                    f"'{record.name}' ({record.package_id}) is a critical, protected core system component. "
                    "Uninstallation is blocked to prevent breaking your operating system."
                ),
            )

        # 2. Locate provider
        provider_id = self._resolve_provider_id(record)
        provider = self._orchestrator.get_provider(provider_id)
        if not provider:
            return UninstallPlan(
                record=record,
                target_summary=f"{record.name} ({record.package_id})",
                commands_to_run=[],
                requires_elevation=record.requires_elevation,
                is_executable=False,
                error_message=f"No active provider available to uninstall {record.source.value} applications.",
            )

        # 3. Request plan from provider
        plan = provider.plan_uninstall(record, keep_data=keep_data)
        return plan

    def execute_plan(
        self,
        plan: UninstallPlan,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> OperationResult:
        """Execute a confirmed uninstall plan with structured result reporting."""
        if not plan.is_executable:
            return OperationResult(
                success=False,
                target_id=plan.record.id,
                message=plan.error_message or "Execution blocked by safety guard.",
            )

        provider_id = self._resolve_provider_id(plan.record)
        provider = self._orchestrator.get_provider(provider_id)
        if not provider:
            return OperationResult(
                success=False,
                target_id=plan.record.id,
                message=f"Provider '{provider_id}' is not available.",
            )

        logger.info("Executing uninstallation for %s via provider %s", plan.record.id, provider_id)
        result = provider.execute_uninstall(plan, progress_callback=progress_callback)
        return result

    def _resolve_provider_id(self, record: InstallationRecord) -> str:
        """Map record source to provider identifier."""
        from appharbor.domain.models import SourceEnum

        mapping = {
            SourceEnum.FLATPAK: "flatpak",
            SourceEnum.RPM: "rpm_dnf",
            SourceEnum.SNAP: "snap",
            SourceEnum.APPIMAGE: "appimage",
            SourceEnum.DEB: "dpkg_apt",
            SourceEnum.PACMAN: "pacman",
            SourceEnum.ZYPPER: "zypper",
            SourceEnum.MANUAL: "manual_desktop",
            SourceEnum.UNKNOWN: "manual_desktop",
        }
        return mapping.get(record.source, "manual_desktop")
