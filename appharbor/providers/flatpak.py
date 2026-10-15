"""Flatpak application provider."""

from __future__ import annotations

import logging
import os
import re
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
from appharbor.system.capabilities import has_command
from appharbor.system.process import run_command_safely

logger = logging.getLogger(__name__)


def _parse_size_string(size_str: str) -> Optional[int]:
    """Parse flatpak human-readable size string (e.g., '18.9 MB', '1.2 GB') to bytes."""
    if not size_str or size_str == "-":
        return None
    # Normalize non-breaking spaces
    s = size_str.replace("\xa0", " ").strip()
    match = re.match(r"^([\d.]+)\s*([KMGTP]?B)$", s, re.IGNORECASE)
    if not match:
        return None
    val, unit = float(match.group(1)), match.group(2).upper()
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4, "PB": 1024**5}
    return int(val * units.get(unit, 1))


class FlatpakProvider(BaseProvider):
    """Discovers and manages Flatpak applications."""

    @property
    def provider_id(self) -> str:
        return "flatpak"

    @property
    def display_name(self) -> str:
        return "Flatpak"

    def detect_capabilities(self) -> ProviderCapabilities:
        if not has_command("flatpak"):
            return ProviderCapabilities(
                provider_id=self.provider_id,
                is_available=False,
                can_inventory=False,
                can_uninstall=False,
                status_message="flatpak CLI not found",
            )

        res = run_command_safely(["flatpak", "--version"])
        ver = res.stdout.strip() if res.is_success else "installed"
        return ProviderCapabilities(
            provider_id=self.provider_id,
            is_available=True,
            version_string=ver,
            can_inventory=True,
            can_uninstall=True,
            can_detect_size=True,
            can_detect_user_data=True,
            default_elevation_required=False,  # User flatpaks don't need elevation; system uses Polkit agent
            status_message=f"Available ({ver})",
        )

    def scan_applications(
        self,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> list[InstallationRecord]:
        caps = self.detect_capabilities()
        if not caps.is_available:
            return []

        if progress_callback:
            progress_callback("Scanning Flatpak applications...", 0.1)

        # Query flatpak for installed apps with columns:
        # application, name, version, branch, arch, origin, installation, size, description, ref
        cmd = [
            "flatpak",
            "list",
            "--app",
            "--columns=application,name,version,branch,arch,origin,installation,size,description,ref",
        ]
        res = run_command_safely(cmd, timeout_seconds=15.0)
        if not res.is_success:
            logger.warning("flatpak list failed: %s", res.stderr)
            return []

        records: list[InstallationRecord] = []
        lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
        total = max(1, len(lines))

        for idx, line in enumerate(lines):
            parts = line.split("\t")
            if len(parts) < 7:
                continue

            app_id = parts[0].strip()
            name = parts[1].strip() or app_id
            version = parts[2].strip() if parts[2].strip() != "-" else None
            branch = parts[3].strip() if len(parts) > 3 else None
            arch = parts[4].strip() if len(parts) > 4 else None
            origin = parts[5].strip() if len(parts) > 5 else None
            installation = parts[6].strip().lower() if len(parts) > 6 else "system"
            size_str = parts[7].strip() if len(parts) > 7 else None
            desc = parts[8].strip() if len(parts) > 8 else None
            ref = parts[9].strip() if len(parts) > 9 else None

            scope = ScopeEnum.USER if installation == "user" else ScopeEnum.SYSTEM
            size_bytes = _parse_size_string(size_str) if size_str else None

            # Look up desktop file and icon
            desktop_path = None
            if scope == ScopeEnum.USER:
                user_desktop = Path.home() / ".local/share/flatpak/exports/share/applications" / f"{app_id}.desktop"
                if user_desktop.exists():
                    desktop_path = str(user_desktop)
            else:
                sys_desktop = Path("/var/lib/flatpak/exports/share/applications") / f"{app_id}.desktop"
                if sys_desktop.exists():
                    desktop_path = str(sys_desktop)

            # Potential user data location
            user_data_path = str(Path.home() / ".var/app" / app_id)
            known_data_paths = [user_data_path] if Path(user_data_path).exists() else []

            # Determine install path
            if scope == ScopeEnum.USER:
                install_root = str(Path.home() / ".local/share/flatpak/app" / app_id)
            else:
                install_root = f"/var/lib/flatpak/app/{app_id}"

            record = InstallationRecord(
                id=f"flatpak:{installation}:{app_id}",
                name=name,
                package_id=app_id,
                source=SourceEnum.FLATPAK,
                scope=scope,
                version=version,
                architecture=arch,
                origin=origin,
                exec_target=f"flatpak run {app_id}",
                desktop_entry_path=desktop_path,
                icon_name_or_path=app_id,
                install_path=install_root,
                installed_size_bytes=size_bytes,
                requires_elevation=(scope == ScopeEnum.SYSTEM),
                is_removable=True,
                confidence=ConfidenceLevel.HIGH,
                description=desc,
                known_data_paths=known_data_paths,
                warnings=[],
            )
            records.append(record)

            if progress_callback and idx % 5 == 0:
                progress_callback(f"Processed Flatpak app {name}", 0.1 + 0.8 * (idx / total))

        if progress_callback:
            progress_callback(f"Found {len(records)} Flatpak applications", 1.0)

        return records

    def plan_uninstall(
        self,
        record: InstallationRecord,
        keep_data: bool = True,
    ) -> UninstallPlan:
        app_id = record.package_id
        scope_flag = "--user" if record.scope == ScopeEnum.USER else "--system"

        args = ["flatpak", "uninstall", "-y", scope_flag]
        if not keep_data:
            args.append("--delete-data")
        args.append(app_id)

        user_data_path = str(Path.home() / ".var/app" / app_id)
        user_data_exists = Path(user_data_path).exists()

        consequences = [
            f"Removes Flatpak application package '{app_id}' ({record.scope.value}).",
        ]
        if keep_data:
            consequences.append(f"Personal configuration and application data in '{user_data_path}' will be preserved.")
        else:
            consequences.append(f"WARNING: Personal data in '{user_data_path}' will be PERMANENTLY deleted.")

        return UninstallPlan(
            record=record,
            target_summary=f"Flatpak application {record.name} ({app_id})",
            commands_to_run=[args],
            requires_elevation=(record.scope == ScopeEnum.SYSTEM),
            preserve_user_data=keep_data,
            user_data_paths=[user_data_path] if user_data_exists else [],
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
        if progress_callback:
            progress_callback(f"Executing: {' '.join(cmd)}")

        res = run_command_safely(cmd, timeout_seconds=120.0)
        if res.is_success:
            return OperationResult(
                success=True,
                target_id=plan.record.id,
                message=f"Successfully uninstalled {plan.record.name}.",
                stdout=res.stdout,
                stderr=res.stderr,
                exit_code=res.exit_code,
            )
        else:
            return OperationResult(
                success=False,
                target_id=plan.record.id,
                message=f"Flatpak uninstall failed: {res.stderr or res.stdout}",
                stdout=res.stdout,
                stderr=res.stderr,
                exit_code=res.exit_code,
            )
