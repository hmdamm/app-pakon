"""Snap application provider."""

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
from appharbor.system.process import run_command_safely

logger = logging.getLogger(__name__)


class SnapProvider(BaseProvider):
    """Discovers and manages Snap applications."""

    @property
    def provider_id(self) -> str:
        return "snap"

    @property
    def display_name(self) -> str:
        return "Snap"

    def detect_capabilities(self) -> ProviderCapabilities:
        if not has_command("snap"):
            return ProviderCapabilities(
                provider_id=self.provider_id,
                is_available=False,
                can_inventory=False,
                can_uninstall=False,
                status_message="snap CLI not found",
            )

        res = run_command_safely(["snap", "version"], timeout_seconds=5.0)
        ver = "installed"
        if res.is_success:
            for line in res.stdout.splitlines():
                if line.startswith("snap "):
                    ver = line.strip()
                    break

        return ProviderCapabilities(
            provider_id=self.provider_id,
            is_available=True,
            version_string=ver,
            can_inventory=True,
            can_uninstall=True,
            can_detect_size=False,
            can_detect_user_data=True,
            default_elevation_required=True,
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
            progress_callback("Querying installed snaps...", 0.2)

        res = run_command_safely(["snap", "list"], timeout_seconds=15.0)
        if not res.is_success:
            logger.warning("snap list failed: %s", res.stderr)
            return []

        records: list[InstallationRecord] = []
        lines = res.stdout.splitlines()
        if not lines:
            return []

        # Skip header: Name  Version  Rev  Tracking  Publisher  Notes
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 3:
                continue

            snap_name = parts[0].strip()
            version = parts[1].strip()
            rev = parts[2].strip()
            tracking = parts[3].strip() if len(parts) > 3 else None
            publisher = parts[4].strip() if len(parts) > 4 else None
            notes = " ".join(parts[5:]) if len(parts) > 5 else None

            # Skip core runtime snaps if classifying desktop apps
            # e.g., bare, core, core18, core20, core22, snapd
            if snap_name in {"bare", "core", "core18", "core20", "core22", "core24", "snapd"}:
                continue

            # Look for desktop entry in /var/lib/snapd/desktop/applications
            desktop_path = None
            snap_desktop = Path(f"/var/lib/snapd/desktop/applications/{snap_name}_{snap_name}.desktop")
            if not snap_desktop.exists():
                snap_desktop = Path(f"/var/lib/snapd/desktop/applications/{snap_name}.desktop")
            if snap_desktop.exists():
                desktop_path = str(snap_desktop)

            user_data = Path.home() / "snap" / snap_name
            known_paths = [str(user_data)] if user_data.exists() else []

            rec = InstallationRecord(
                id=f"snap:system:{snap_name}",
                name=snap_name.capitalize(),
                package_id=snap_name,
                source=SourceEnum.SNAP,
                scope=ScopeEnum.SYSTEM,
                version=version,
                architecture=None,
                origin=f"Snap Store ({tracking or 'stable'})",
                exec_target=f"snap run {snap_name}",
                desktop_entry_path=desktop_path,
                icon_name_or_path=snap_name,
                install_path=f"/snap/{snap_name}/{rev}",
                requires_elevation=True,
                is_removable=True,
                confidence=ConfidenceLevel.HIGH,
                description=f"Snap package by {publisher or 'unknown'}. Notes: {notes or 'standard'}",
                known_data_paths=known_paths,
                warnings=[],
            )
            records.append(rec)

        if progress_callback:
            progress_callback(f"Found {len(records)} Snap applications", 1.0)

        return records

    def plan_uninstall(
        self,
        record: InstallationRecord,
        keep_data: bool = True,
    ) -> UninstallPlan:
        snap_name = record.package_id
        elev_tool = get_elevation_tool() or "pkexec"

        # By default snap creates a snapshot of data when removed unless --purge is specified
        cmd = [elev_tool, "snap", "remove"]
        if not keep_data:
            cmd.append("--purge")
        cmd.append(snap_name)

        user_data = Path.home() / "snap" / snap_name
        consequences = [
            f"Removes snap package '{snap_name}'.",
        ]
        if keep_data:
            consequences.append("Snapd will create a 31-day snapshot of user data before removal.")
        else:
            consequences.append(f"WARNING: User data in '{user_data}' and snapshots will be PERMANENTLY purged.")

        return UninstallPlan(
            record=record,
            target_summary=f"Snap package {record.name} ({snap_name})",
            commands_to_run=[cmd],
            requires_elevation=True,
            preserve_user_data=keep_data,
            user_data_paths=[str(user_data)] if user_data.exists() else [],
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
            progress_callback(f"Removing snap: {' '.join(cmd)}")

        res = run_command_safely(cmd, timeout_seconds=180.0)
        if res.is_success:
            return OperationResult(
                success=True,
                target_id=plan.record.id,
                message=f"Successfully removed snap {plan.record.name}.",
                stdout=res.stdout,
                stderr=res.stderr,
                exit_code=res.exit_code,
            )
        else:
            return OperationResult(
                success=False,
                target_id=plan.record.id,
                message=f"Snap removal failed: {res.stderr or res.stdout}",
                stdout=res.stdout,
                stderr=res.stderr,
                exit_code=res.exit_code,
            )
