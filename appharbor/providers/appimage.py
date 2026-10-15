"""AppImage provider for portable Linux applications."""

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
from appharbor.system.capabilities import get_elevation_tool
from appharbor.system.desktop_entry import parse_desktop_file
from appharbor.system.process import run_command_safely

logger = logging.getLogger(__name__)


def is_appimage_binary(path: Path) -> bool:
    """Check if a file is an AppImage using ELF headers without executing it."""
    try:
        if not path.is_file() or path.is_symlink():
            return False
        # Must be at least 16 bytes for header inspection
        if path.stat().st_size < 16:
            return False

        with open(path, "rb") as f:
            header = f.read(16)
            # ELF magic
            if header[0:4] != b"\x7fELF":
                return False
            # AppImage Type 1 or Type 2 magic at offset 8
            # Type 1: 0x41 0x49 0x01 ('AI\x01')
            # Type 2: 0x41 0x49 0x02 ('AI\x02')
            if header[8:10] == b"AI" and header[10] in (1, 2):
                return True
    except Exception:
        pass
    return False


def parse_appimage_filename(filename: str) -> tuple[str, Optional[str]]:
    """Extract display name and version from AppImage filename."""
    # Strip extension
    base = re.sub(r"\.appimage$", "", filename, flags=re.IGNORECASE)
    # Match patterns like Name-1.2.3-x86_64 or Name_1.2.3
    m = re.match(r"^([a-zA-Z0-9_\-\s]+?)[-_vV](\d+[\d\.\-_a-zA-Z]*?)(?:[-_](x86_64|i386|aarch64|arm64))?$", base)
    if m:
        name = m.group(1).replace("-", " ").replace("_", " ").strip().title()
        version = m.group(2).strip()
        return name, version
    return base.replace("-", " ").replace("_", " ").strip().title(), None


class AppImageProvider(BaseProvider):
    """Discovers and manages standalone AppImage applications."""

    @property
    def provider_id(self) -> str:
        return "appimage"

    @property
    def display_name(self) -> str:
        return "AppImage"

    def detect_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id=self.provider_id,
            is_available=True,
            version_string="Type 1 & 2 scanner",
            can_inventory=True,
            can_uninstall=True,
            can_detect_size=True,
            can_detect_user_data=False,
            default_elevation_required=False,
            status_message="Available (Filesystem discovery)",
        )

    def scan_applications(
        self,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> list[InstallationRecord]:
        if progress_callback:
            progress_callback("Scanning common AppImage directories...", 0.1)

        home = Path.home()
        candidate_dirs = [
            home / ".local/bin",
            home / "Applications",
            home / "Desktop",
            home / "Downloads",
            Path("/opt"),
            Path("/usr/local/bin"),
        ]

        found_files: set[Path] = set()

        # 1. Scan candidate directories for .AppImage or .appimage
        for cdir in candidate_dirs:
            if cdir.exists() and cdir.is_dir():
                try:
                    for entry in cdir.iterdir():
                        if entry.name.lower().endswith(".appimage") and entry.is_file():
                            found_files.add(entry.resolve())
                        elif entry.is_file() and is_appimage_binary(entry):
                            found_files.add(entry.resolve())
                except (PermissionError, OSError):
                    pass

        # 2. Inspect user desktop entries for AppImage Exec paths
        user_apps_dir = home / ".local/share/applications"
        desktop_to_file: dict[Path, str] = {}
        if user_apps_dir.exists():
            for df in user_apps_dir.glob("*.desktop"):
                d_entry = parse_desktop_file(df)
                if d_entry and d_entry.clean_exec:
                    # Exec might start with quotes or path
                    exec_token = d_entry.clean_exec.split()[0].strip("\"'")
                    p = Path(exec_token)
                    if p.is_file() and (p.name.lower().endswith(".appimage") or is_appimage_binary(p)):
                        resolved = p.resolve()
                        found_files.add(resolved)
                        desktop_to_file[resolved] = str(df)

        records: list[InstallationRecord] = []
        for apath in sorted(found_files):
            try:
                st = apath.stat()
                size_bytes = st.st_size
            except Exception:
                size_bytes = None

            parsed_name, version = parse_appimage_filename(apath.name)
            desktop_path = desktop_to_file.get(apath)

            icon = None
            if desktop_path:
                de = parse_desktop_file(desktop_path)
                if de and de.name:
                    parsed_name = de.name
                if de and de.icon:
                    icon = de.icon

            is_user = str(apath).startswith(str(home))
            scope = ScopeEnum.USER if is_user else ScopeEnum.SYSTEM

            pkg_id = apath.stem.lower().replace(" ", "-")

            rec = InstallationRecord(
                id=f"appimage:{scope.value.lower()}:{pkg_id}",
                name=parsed_name,
                package_id=apath.name,
                source=SourceEnum.APPIMAGE,
                scope=scope,
                version=version,
                architecture="x86_64" if "x86_64" in apath.name else None,
                origin=f"Local file ({apath.parent})",
                exec_target=str(apath),
                desktop_entry_path=desktop_path,
                icon_name_or_path=icon or "application-x-executable",
                install_path=str(apath),
                installed_size_bytes=size_bytes,
                requires_elevation=not is_user,
                is_removable=True,
                confidence=ConfidenceLevel.HIGH,
                description=f"Standalone portable AppImage: {apath.name}",
                known_data_paths=[],
                warnings=[],
            )
            records.append(rec)

        if progress_callback:
            progress_callback(f"Found {len(records)} AppImages", 1.0)

        return records

    def plan_uninstall(
        self,
        record: InstallationRecord,
        keep_data: bool = True,
    ) -> UninstallPlan:
        app_path = Path(record.install_path or "")
        desktop_path = Path(record.desktop_entry_path) if record.desktop_entry_path else None

        if not app_path.exists() or not app_path.is_file():
            return UninstallPlan(
                record=record,
                target_summary=f"AppImage {record.name}",
                commands_to_run=[],
                requires_elevation=record.requires_elevation,
                is_executable=False,
                error_message=f"AppImage file not found at {app_path}",
            )

        commands: list[list[str]] = []
        paths_to_delete = [str(app_path)]

        # If desktop integration file exists, remove it too
        if desktop_path and desktop_path.exists():
            paths_to_delete.append(str(desktop_path))

        consequences = [
            f"Removes the standalone AppImage executable: '{app_path}'.",
        ]
        if desktop_path and desktop_path.exists():
            consequences.append(f"Removes associated desktop integration launcher: '{desktop_path}'.")

        return UninstallPlan(
            record=record,
            target_summary=f"AppImage {record.name} ({app_path.name})",
            commands_to_run=[["rm", "-f", p] for p in paths_to_delete],
            requires_elevation=record.requires_elevation,
            paths_to_delete=paths_to_delete,
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

        deleted = []
        for p_str in plan.paths_to_delete:
            p = Path(p_str)
            if progress_callback:
                progress_callback(f"Deleting {p}...")

            if not p.exists():
                continue

            # If elevation is required
            if plan.requires_elevation:
                elev = get_elevation_tool() or "pkexec"
                res = run_command_safely([elev, "rm", "-f", str(p)])
                if not res.is_success:
                    return OperationResult(
                        success=False,
                        target_id=plan.record.id,
                        message=f"Failed to delete {p}: {res.stderr}",
                    )
            else:
                try:
                    p.unlink()
                    deleted.append(p_str)
                except Exception as exc:
                    return OperationResult(
                        success=False,
                        target_id=plan.record.id,
                        message=f"Failed to delete {p}: {exc}",
                    )

        return OperationResult(
            success=True,
            target_id=plan.record.id,
            message=f"Successfully removed AppImage {plan.record.name}.",
        )
