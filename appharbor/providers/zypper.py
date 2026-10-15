"""Zypper provider for openSUSE and SUSE Linux Enterprise."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from appharbor.domain.models import (
    InstallationRecord,
    OperationResult,
    ProviderCapabilities,
    UninstallPlan,
)
from appharbor.providers.base import BaseProvider
from appharbor.providers.rpm_dnf import RpmDnfProvider
from appharbor.system.capabilities import get_elevation_tool, has_command
from appharbor.system.process import run_command_safely
from appharbor.uninstall.guards import is_critical_package

logger = logging.getLogger(__name__)


class ZypperProvider(BaseProvider):
    """Discovers and manages openSUSE native applications using RPM and Zypper."""

    def __init__(self):
        self._rpm_provider = RpmDnfProvider()

    @property
    def provider_id(self) -> str:
        return "zypper"

    @property
    def display_name(self) -> str:
        return "Zypper / RPM"

    def detect_capabilities(self) -> ProviderCapabilities:
        if not has_command("zypper") or not has_command("rpm"):
            return ProviderCapabilities(
                provider_id=self.provider_id,
                is_available=False,
                can_inventory=False,
                can_uninstall=False,
                status_message="zypper not found",
            )

        return ProviderCapabilities(
            provider_id=self.provider_id,
            is_available=True,
            version_string="zypper",
            can_inventory=True,
            can_uninstall=True,
            can_detect_size=True,
            can_detect_user_data=False,
            default_elevation_required=True,
            status_message="Available",
        )

    def scan_applications(
        self,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> list[InstallationRecord]:
        caps = self.detect_capabilities()
        if not caps.is_available:
            return []

        # Delegate inventory to RPM inspection
        return self._rpm_provider.scan_applications(progress_callback=progress_callback)

    def plan_uninstall(
        self,
        record: InstallationRecord,
        keep_data: bool = True,
    ) -> UninstallPlan:
        pkg_name = record.package_id
        if is_critical_package(pkg_name):
            return UninstallPlan(
                record=record,
                target_summary=f"Critical system package {record.name} ({pkg_name})",
                commands_to_run=[],
                requires_elevation=True,
                is_critical_warning=True,
                is_executable=False,
                error_message=f"'{pkg_name}' is a critical operating system component.",
            )

        elev = get_elevation_tool() or "pkexec"
        cmd = [elev, "zypper", "rm", "-y", pkg_name]

        consequences = [
            f"Removes openSUSE RPM package '{pkg_name}' via zypper.",
            "User configuration in ~ is preserved.",
        ]

        return UninstallPlan(
            record=record,
            target_summary=f"Zypper package {record.name} ({pkg_name})",
            commands_to_run=[cmd],
            requires_elevation=True,
            preserve_user_data=keep_data,
            consequences_summary="\n".join(consequences),
            is_critical_warning=False,
            is_executable=True,
        )

    def execute_uninstall(
        self,
        plan: UninstallPlan,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> OperationResult:
        if not plan.is_executable or not plan.commands_to_run:
            return OperationResult(
                success=False,
                target_id=plan.record.id,
                message=plan.error_message or "Invalid uninstall plan",
            )

        cmd = plan.commands_to_run[0]
        res = run_command_safely(cmd, timeout_seconds=180.0)
        return OperationResult(
            success=res.is_success,
            target_id=plan.record.id,
            message=f"Removed {plan.record.name}." if res.is_success else f"zypper failed: {res.stderr or res.stdout}",
            stdout=res.stdout,
            stderr=res.stderr,
            exit_code=res.exit_code,
        )
