"""Pacman provider for Arch Linux and derivatives."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from appharbor.domain.models import (
    ConfidenceLevel,
    InstallationRecord,
    OperationResult,
    ProviderCapabilities,
    ScopeEnum,
    SourceEnum,
    UninstallPlan,
)
from appharbor.providers.base import BaseProvider
from appharbor.system.capabilities import get_elevation_tool, has_command
from appharbor.system.desktop_entry import parse_desktop_file
from appharbor.system.process import run_command_safely
from appharbor.uninstall.guards import is_critical_package

logger = logging.getLogger(__name__)


class PacmanProvider(BaseProvider):
    """Discovers and manages Arch Linux native applications."""

    @property
    def provider_id(self) -> str:
        return "pacman"

    @property
    def display_name(self) -> str:
        return "Pacman"

    def detect_capabilities(self) -> ProviderCapabilities:
        if not has_command("pacman"):
            return ProviderCapabilities(
                provider_id=self.provider_id,
                is_available=False,
                can_inventory=False,
                can_uninstall=False,
                status_message="pacman not found",
            )

        return ProviderCapabilities(
            provider_id=self.provider_id,
            is_available=True,
            version_string="pacman",
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

        search_dirs = [Path("/usr/share/applications"), Path("/usr/local/share/applications")]
        desktop_files: list[Path] = []
        for sdir in search_dirs:
            if sdir.exists():
                desktop_files.extend(sdir.glob("*.desktop"))

        records: list[InstallationRecord] = []
        seen_packages: set[str] = set()

        for df in desktop_files:
            entry = parse_desktop_file(df)
            if not entry or not entry.is_visible_app:
                continue

            # Query pacman -Qo for ownership
            res = run_command_safely(["pacman", "-Qo", str(df.resolve())], timeout_seconds=3.0)
            if not res.is_success or not res.stdout.strip():
                continue

            # Output: "/usr/share/applications/file.desktop is owned by package-name version"
            line = res.stdout.splitlines()[0]
            if "is owned by" not in line:
                continue
            owner_info = line.split("is owned by")[-1].strip().split()
            pkg_name = owner_info[0]
            version = owner_info[1] if len(owner_info) > 1 else None

            if pkg_name in seen_packages:
                continue
            seen_packages.add(pkg_name)

            critical = is_critical_package(pkg_name)
            rec = InstallationRecord(
                id=f"pacman:system:{pkg_name}",
                name=entry.name,
                package_id=pkg_name,
                source=SourceEnum.PACMAN,
                scope=ScopeEnum.SYSTEM,
                version=version,
                architecture=None,
                origin="Arch Repository",
                exec_target=entry.clean_exec,
                desktop_entry_path=str(df.resolve()),
                icon_name_or_path=entry.icon,
                install_path="/usr",
                installed_size_bytes=None,
                requires_elevation=True,
                is_removable=not critical,
                is_critical_system_package=critical,
                confidence=ConfidenceLevel.HIGH,
                description=entry.comment,
                known_data_paths=[],
                warnings=["Protected core system component"] if critical else [],
            )
            records.append(rec)

        return records

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
        cmd = [elev, "pacman", "-R", "--noconfirm", pkg_name]

        consequences = [
            f"Removes Arch package '{pkg_name}' via pacman.",
            "User configuration in ~ is preserved.",
        ]

        return UninstallPlan(
            record=record,
            target_summary=f"Pacman package {record.name} ({pkg_name})",
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
            message=f"Removed {plan.record.name}." if res.is_success else f"pacman failed: {res.stderr or res.stdout}",
            stdout=res.stdout,
            stderr=res.stderr,
            exit_code=res.exit_code,
        )
