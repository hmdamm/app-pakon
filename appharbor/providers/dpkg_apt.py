"""Dpkg / APT provider for Debian, Ubuntu, and derivatives."""

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


class DpkgAptProvider(BaseProvider):
    """Discovers and manages Debian/APT native applications."""

    @property
    def provider_id(self) -> str:
        return "dpkg_apt"

    @property
    def display_name(self) -> str:
        return "DEB / APT"

    def detect_capabilities(self) -> ProviderCapabilities:
        if not has_command("dpkg") or not has_command("apt-get"):
            return ProviderCapabilities(
                provider_id=self.provider_id,
                is_available=False,
                can_inventory=False,
                can_uninstall=False,
                status_message="dpkg/apt not found",
            )

        return ProviderCapabilities(
            provider_id=self.provider_id,
            is_available=True,
            version_string="dpkg + apt",
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

            # Query dpkg -S for ownership
            res = run_command_safely(["dpkg", "-S", str(df.resolve())], timeout_seconds=3.0)
            if not res.is_success or not res.stdout.strip():
                continue

            # Output: "package-name: /usr/share/applications/file.desktop"
            line = res.stdout.splitlines()[0]
            pkg_name = line.split(":")[0].strip()

            if pkg_name in seen_packages:
                continue
            seen_packages.add(pkg_name)

            # Query package info via dpkg-query
            q_res = run_command_safely([
                "dpkg-query",
                "-W",
                "-f=${Package}|${Version}|${Architecture}|${Installed-Size}\n",
                pkg_name,
            ])
            version = None
            arch = None
            size_bytes = None
            if q_res.is_success and q_res.stdout.strip():
                q_parts = q_res.stdout.strip().split("|")
                if len(q_parts) >= 2:
                    version = q_parts[1].strip()
                if len(q_parts) >= 3:
                    arch = q_parts[2].strip()
                if len(q_parts) >= 4:
                    try:
                        # dpkg installed size is in KB
                        size_bytes = int(q_parts[3].strip()) * 1024
                    except (ValueError, TypeError):
                        pass

            critical = is_critical_package(pkg_name)
            rec = InstallationRecord(
                id=f"deb:system:{pkg_name}",
                name=entry.name,
                package_id=pkg_name,
                source=SourceEnum.DEB,
                scope=ScopeEnum.SYSTEM,
                version=version,
                architecture=arch,
                origin="APT repository",
                exec_target=entry.clean_exec,
                desktop_entry_path=str(df.resolve()),
                icon_name_or_path=entry.icon,
                install_path="/usr",
                installed_size_bytes=size_bytes,
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
        action = "remove" if keep_data else "purge"
        cmd = [elev, "apt-get", action, "-y", pkg_name]

        consequences = [
            f"Removes native DEB package '{pkg_name}' via APT ({action}).",
            "Dependencies will be checked by APT before proceeding.",
        ]
        if keep_data:
            consequences.append("System configuration files in /etc and user data are preserved.")
        else:
            consequences.append("Configuration files will be purged.")

        return UninstallPlan(
            record=record,
            target_summary=f"DEB package {record.name} ({pkg_name})",
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
            message=f"Removed {plan.record.name}." if res.is_success else f"APT failed: {res.stderr or res.stdout}",
            stdout=res.stdout,
            stderr=res.stderr,
            exit_code=res.exit_code,
        )
