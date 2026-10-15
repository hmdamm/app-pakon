"""Manual / Unknown desktop applications provider."""

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
from appharbor.system.capabilities import get_elevation_tool
from appharbor.system.desktop_entry import DesktopEntry, parse_desktop_file
from appharbor.system.process import run_command_safely

logger = logging.getLogger(__name__)


class ManualDesktopProvider(BaseProvider):
    """Discovers manual, local, or unmanaged desktop application launchers."""

    def __init__(self, claimed_desktop_paths: Optional[set[str]] = None):
        self._claimed_paths = claimed_desktop_paths or set()

    def set_claimed_paths(self, claimed: set[str]) -> None:
        """Register desktop file paths already claimed by other providers (RPM, Flatpak, etc.)."""
        self._claimed_paths = set(claimed)

    @property
    def provider_id(self) -> str:
        return "manual_desktop"

    @property
    def display_name(self) -> str:
        return "Manual / Unknown"

    def detect_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id=self.provider_id,
            is_available=True,
            version_string="Desktop entry inspector",
            can_inventory=True,
            can_uninstall=True,
            can_detect_size=False,
            can_detect_user_data=False,
            default_elevation_required=False,
            status_message="Available",
        )

    def scan_applications(
        self,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> list[InstallationRecord]:
        home = Path.home()
        search_dirs = [
            (home / ".local/share/applications", ScopeEnum.USER),
            (Path("/usr/local/share/applications"), ScopeEnum.SYSTEM),
        ]

        records: list[InstallationRecord] = []
        for sdir, scope in search_dirs:
            if not sdir.exists():
                continue

            for df in sdir.glob("*.desktop"):
                resolved_str = str(df.resolve())
                # Skip if already claimed by Flatpak, RPM, Snap, or AppImage
                if resolved_str in self._claimed_paths or str(df) in self._claimed_paths:
                    continue

                entry = parse_desktop_file(df)
                if not entry or not entry.is_visible_app:
                    continue

                # Check if it mentions flatpak or snap in Exec line
                clean_exec = entry.clean_exec or ""
                if "flatpak run" in clean_exec:
                    continue
                if clean_exec.startswith("/snap/bin/"):
                    continue
                if clean_exec.lower().endswith(".appimage"):
                    continue

                # Check if target executable exists to estimate size or path
                exec_target = clean_exec.split()[0].strip("\"'") if clean_exec else None
                target_path = Path(exec_target) if exec_target else None
                size_bytes = None
                if target_path and target_path.is_file():
                    try:
                        size_bytes = target_path.stat().st_size
                    except Exception:
                        pass

                pkg_id = df.stem
                rec = InstallationRecord(
                    id=f"manual:{scope.value.lower()}:{pkg_id}",
                    name=entry.name,
                    package_id=pkg_id,
                    source=SourceEnum.UNKNOWN,
                    scope=scope,
                    version=None,
                    architecture=None,
                    origin=f"Desktop launcher ({df.parent})",
                    exec_target=entry.clean_exec,
                    desktop_entry_path=resolved_str,
                    icon_name_or_path=entry.icon or "application-x-executable",
                    install_path=str(target_path) if target_path and target_path.exists() else resolved_str,
                    installed_size_bytes=size_bytes,
                    requires_elevation=(scope == ScopeEnum.SYSTEM),
                    is_removable=True,
                    confidence=ConfidenceLevel.LOW,
                    description=entry.comment or "Application launcher not managed by any known package manager.",
                    known_data_paths=[],
                    warnings=["Origin cannot be verified automatically. Uninstallation removes the desktop entry launcher."],
                )
                records.append(rec)

        return records

    def plan_uninstall(
        self,
        record: InstallationRecord,
        keep_data: bool = True,
    ) -> UninstallPlan:
        desktop_path = Path(record.desktop_entry_path or "")
        if not desktop_path.exists():
            return UninstallPlan(
                record=record,
                target_summary=f"Desktop launcher {record.name}",
                commands_to_run=[],
                requires_elevation=record.requires_elevation,
                is_executable=False,
                error_message=f"Desktop entry file not found at {desktop_path}",
            )

        consequences = [
            f"Removes the desktop application launcher: '{desktop_path}'.",
            "Notice: Because this application was installed manually, underlying binaries or scripts outside this launcher will not be deleted automatically.",
        ]

        return UninstallPlan(
            record=record,
            target_summary=f"Manual launcher {record.name} ({record.package_id})",
            commands_to_run=[["rm", "-f", str(desktop_path)]],
            requires_elevation=record.requires_elevation,
            paths_to_delete=[str(desktop_path)],
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
        if not plan.is_executable or not plan.paths_to_delete:
            return OperationResult(
                success=False,
                target_id=plan.record.id,
                message=plan.error_message or "Invalid uninstall plan",
            )

        target_file = Path(plan.paths_to_delete[0])
        if plan.requires_elevation:
            elev = get_elevation_tool() or "pkexec"
            res = run_command_safely([elev, "rm", "-f", str(target_file)])
            if not res.is_success:
                return OperationResult(
                    success=False,
                    target_id=plan.record.id,
                    message=f"Failed to remove launcher: {res.stderr}",
                )
        else:
            try:
                target_file.unlink()
            except Exception as exc:
                return OperationResult(
                    success=False,
                    target_id=plan.record.id,
                    message=f"Failed to remove launcher: {exc}",
                )

        return OperationResult(
            success=True,
            target_id=plan.record.id,
            message=f"Removed desktop launcher for {plan.record.name}.",
        )
