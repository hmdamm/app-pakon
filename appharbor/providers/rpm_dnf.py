"""RPM / DNF application provider for Fedora, RHEL, and compatible distributions."""

from __future__ import annotations

import glob
import logging
from concurrent.futures import ThreadPoolExecutor
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
from appharbor.system.desktop_entry import DesktopEntry, parse_desktop_file
from appharbor.system.process import run_command_safely
from appharbor.uninstall.guards import is_critical_package

logger = logging.getLogger(__name__)


class RpmDnfProvider(BaseProvider):
    """Discovers and manages RPM-packaged native applications."""

    @property
    def provider_id(self) -> str:
        return "rpm_dnf"

    @property
    def display_name(self) -> str:
        return "RPM / DNF"

    def detect_capabilities(self) -> ProviderCapabilities:
        if not has_command("rpm"):
            return ProviderCapabilities(
                provider_id=self.provider_id,
                is_available=False,
                can_inventory=False,
                can_uninstall=False,
                status_message="rpm tool not found",
            )

        dnf_tool = "dnf5" if has_command("dnf5") else ("dnf" if has_command("dnf") else "rpm")
        return ProviderCapabilities(
            provider_id=self.provider_id,
            is_available=True,
            version_string=dnf_tool,
            can_inventory=True,
            can_uninstall=has_command("dnf") or has_command("dnf5"),
            can_detect_size=True,
            can_detect_user_data=False,
            default_elevation_required=True,
            status_message=f"Available ({dnf_tool})",
        )

    def _query_rpm_file(self, desktop_path: str) -> Optional[tuple[str, dict[str, str]]]:
        """Query rpm for ownership of a single desktop file."""
        cmd = [
            "rpm",
            "-qf",
            "--queryformat",
            "%{NAME}\t%{VERSION}-%{RELEASE}\t%{ARCH}\t%{SIZE}\t%{INSTALLTIME}\t%{SUMMARY}\n",
            desktop_path,
        ]
        res = run_command_safely(cmd, timeout_seconds=5.0)
        if not res.is_success or not res.stdout.strip():
            return None

        line = res.stdout.splitlines()[0].strip()
        parts = line.split("\t")
        if len(parts) < 6:
            return None

        data = {
            "name": parts[0].strip(),
            "version": parts[1].strip(),
            "arch": parts[2].strip(),
            "size": parts[3].strip(),
            "installtime": parts[4].strip(),
            "summary": parts[5].strip(),
        }
        return desktop_path, data

    def scan_applications(
        self,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> list[InstallationRecord]:
        caps = self.detect_capabilities()
        if not caps.is_available:
            return []

        if progress_callback:
            progress_callback("Finding desktop applications...", 0.05)

        search_dirs = ["/usr/share/applications", "/usr/local/share/applications"]
        desktop_files: list[Path] = []
        for sdir in search_dirs:
            p = Path(sdir)
            if p.exists():
                desktop_files.extend(p.glob("*.desktop"))

        # Parse and filter visible applications
        valid_entries: list[DesktopEntry] = []
        for df in desktop_files:
            entry = parse_desktop_file(df)
            if entry and entry.is_visible_app:
                valid_entries.append(entry)

        if not valid_entries:
            return []

        if progress_callback:
            progress_callback(f"Matching {len(valid_entries)} applications with RPM database...", 0.15)

        # Query RPM ownership in parallel
        results: list[tuple[str, dict[str, str]]] = []
        file_to_entry = {e.file_path: e for e in valid_entries}

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(self._query_rpm_file, e.file_path) for e in valid_entries]
            for i, fut in enumerate(futures):
                res = fut.result()
                if res:
                    results.append(res)
                if progress_callback and i % 10 == 0:
                    progress_callback(
                        "Scanning RPM packages...",
                        0.2 + 0.7 * (i / max(1, len(futures))),
                    )

        records: list[InstallationRecord] = []
        seen_pkg_names: set[str] = set()

        for dpath, rpm_info in results:
            entry = file_to_entry.get(dpath)
            if not entry:
                continue

            pkg_name = rpm_info["name"]
            # Deduplicate by package name if multiple desktop files exist for one package
            if pkg_name in seen_pkg_names:
                continue
            seen_pkg_names.add(pkg_name)

            size_bytes = None
            try:
                size_bytes = int(rpm_info["size"])
            except (ValueError, TypeError):
                pass

            critical = is_critical_package(pkg_name)
            display_name = entry.name or rpm_info["summary"] or pkg_name

            # Look for known user config directory
            cfg_dir = Path.home() / ".config" / pkg_name
            known_paths = [str(cfg_dir)] if cfg_dir.exists() else []

            rec = InstallationRecord(
                id=f"rpm:system:{pkg_name}",
                name=display_name,
                package_id=pkg_name,
                source=SourceEnum.RPM,
                scope=ScopeEnum.SYSTEM,
                version=rpm_info["version"],
                architecture=rpm_info["arch"],
                origin="RPM repository / DNF",
                exec_target=entry.clean_exec,
                desktop_entry_path=dpath,
                icon_name_or_path=entry.icon,
                install_path="/usr",
                installed_size_bytes=size_bytes,
                requires_elevation=True,
                is_removable=not critical,
                is_critical_system_package=critical,
                confidence=ConfidenceLevel.HIGH,
                description=rpm_info["summary"] or entry.comment,
                known_data_paths=known_paths,
                warnings=["Protected core system component"] if critical else [],
            )
            records.append(rec)

        if progress_callback:
            progress_callback(f"Found {len(records)} RPM applications", 1.0)

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
                error_message=(
                    f"'{pkg_name}' is a critical operating system component. "
                    "Uninstallation is disabled to prevent breaking your system."
                ),
            )

        dnf_cmd = "dnf5" if has_command("dnf5") else "dnf"
        elev_tool = get_elevation_tool() or "pkexec"
        cmd = [elev_tool, dnf_cmd, "remove", "-y", pkg_name]

        consequences = [
            f"Removes native RPM package '{pkg_name}' via {dnf_cmd}.",
            "System package manager will check dependencies before completing the removal.",
            "Personal data in user home directory is preserved by default.",
        ]

        return UninstallPlan(
            record=record,
            target_summary=f"RPM package {record.name} ({pkg_name})",
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
        if progress_callback:
            progress_callback(f"Running package manager: {' '.join(cmd)}")

        res = run_command_safely(cmd, timeout_seconds=180.0)
        if res.is_success:
            return OperationResult(
                success=True,
                target_id=plan.record.id,
                message=f"Successfully removed {plan.record.name}.",
                stdout=res.stdout,
                stderr=res.stderr,
                exit_code=res.exit_code,
            )
        else:
            return OperationResult(
                success=False,
                target_id=plan.record.id,
                message=f"Uninstallation failed: {res.stderr or res.stdout}",
                stdout=res.stdout,
                stderr=res.stderr,
                exit_code=res.exit_code,
            )
