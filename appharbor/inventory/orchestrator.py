"""Inventory orchestrator for managing scans, normalization, and filtering."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Optional

from appharbor.domain.models import (
    FilterCategory,
    InstallationRecord,
    ProviderCapabilities,
    ScopeEnum,
    SourceEnum,
)
from appharbor.providers.appimage import AppImageProvider
from appharbor.providers.base import BaseProvider
from appharbor.providers.dpkg_apt import DpkgAptProvider
from appharbor.providers.flatpak import FlatpakProvider
from appharbor.providers.manual_desktop import ManualDesktopProvider
from appharbor.providers.pacman import PacmanProvider
from appharbor.providers.rpm_dnf import RpmDnfProvider
from appharbor.providers.snap import SnapProvider
from appharbor.providers.zypper import ZypperProvider

logger = logging.getLogger(__name__)


@dataclass
class InventorySnapshot:
    """Immutable snapshot of an inventory scan."""
    records: list[InstallationRecord]
    provider_capabilities: dict[str, ProviderCapabilities]
    provider_errors: dict[str, str] = field(default_factory=dict)
    scan_timestamp: float = 0.0

    @property
    def total_count(self) -> int:
        return len(self.records)

    def count_by_filter(self, category: FilterCategory) -> int:
        return sum(1 for r in self.records if r.matches_filter(category))


class InventoryOrchestrator:
    """Coordinates multi-provider application discovery and normalization."""

    def __init__(
        self,
        providers: Optional[list[BaseProvider]] = None,
        manual_provider: Optional[BaseProvider] = None,
        include_manual: bool = True,
    ):
        if providers is not None:
            self._providers = providers
        else:
            # Default auto-detected provider suite
            self._providers = [
                FlatpakProvider(),
                RpmDnfProvider(),
                SnapProvider(),
                AppImageProvider(),
                DpkgAptProvider(),
                PacmanProvider(),
                ZypperProvider(),
            ]
        self._include_manual = include_manual
        self._manual_provider = manual_provider or ManualDesktopProvider()
        self._last_snapshot: Optional[InventorySnapshot] = None

    @property
    def current_snapshot(self) -> Optional[InventorySnapshot]:
        return self._last_snapshot

    def get_provider(self, provider_id: str) -> Optional[BaseProvider]:
        """Find provider by ID."""
        for p in self._providers:
            if p.provider_id == provider_id:
                return p
        if self._manual_provider.provider_id == provider_id:
            return self._manual_provider
        return None

    def scan_all(
        self,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> InventorySnapshot:
        """Execute a full scan across all active providers with failure isolation."""
        import time

        start_time = time.time()
        caps_dict: dict[str, ProviderCapabilities] = {}
        active_providers: list[BaseProvider] = []

        if progress_callback:
            progress_callback("Checking package manager capabilities...", 0.05)

        for p in self._providers:
            try:
                caps = p.detect_capabilities()
                caps_dict[p.provider_id] = caps
                if caps.is_available:
                    active_providers.append(p)
            except Exception as exc:
                logger.error("Provider %s failed during capability check: %s", p.provider_id, exc)
                caps_dict[p.provider_id] = ProviderCapabilities(
                    provider_id=p.provider_id,
                    is_available=False,
                    status_message=f"Error: {exc}",
                )

        all_records: list[InstallationRecord] = []
        provider_errors: dict[str, str] = {}
        claimed_desktop_paths: set[str] = set()

        if progress_callback:
            progress_callback(f"Scanning across {len(active_providers)} active providers...", 0.1)

        # Run provider scans concurrently
        total_active = len(active_providers)
        with ThreadPoolExecutor(max_workers=max(1, min(6, total_active))) as pool:
            future_to_provider = {
                pool.submit(p.scan_applications): p for p in active_providers
            }
            completed_count = 0
            for fut in as_completed(future_to_provider):
                p = future_to_provider[fut]
                completed_count += 1
                try:
                    recs = fut.result()
                    all_records.extend(recs)
                    for r in recs:
                        if r.desktop_entry_path:
                            claimed_desktop_paths.add(r.desktop_entry_path)
                    logger.info("Provider %s found %d apps", p.provider_id, len(recs))
                except Exception as exc:
                    logger.error("Provider %s scan crashed: %s", p.provider_id, exc)
                    provider_errors[p.provider_id] = str(exc)

                if progress_callback:
                    pct = 0.1 + 0.7 * (completed_count / max(1, total_active))
                    progress_callback(f"Finished scanning {p.display_name}...", pct)

        # Now scan Manual / Unknown desktop entries with claimed paths excluded
        if self._include_manual:
            try:
                if hasattr(self._manual_provider, "set_claimed_paths"):
                    self._manual_provider.set_claimed_paths(claimed_desktop_paths)
                manual_recs = self._manual_provider.scan_applications()
                all_records.extend(manual_recs)
                caps_dict[self._manual_provider.provider_id] = self._manual_provider.detect_capabilities()
            except Exception as exc:
                logger.error("Manual desktop provider failed: %s", exc)
                provider_errors[self._manual_provider.provider_id] = str(exc)

        # Deduplication & Cross-Source Annotation
        # Important requirement: Do NOT merge distinct installations into one ambiguous record!
        # Instead, annotate duplicate app names so the user understands both exist.
        name_to_records: dict[str, list[InstallationRecord]] = {}
        for r in all_records:
            clean_name = r.name.strip().lower()
            name_to_records.setdefault(clean_name, []).append(r)

        for clean_name, recs in name_to_records.items():
            if len(recs) > 1:
                # Multiple installations of this app exist!
                sources_str = ", ".join(f"{r.source.value} ({r.scope.value})" for r in recs)
                for r in recs:
                    r.warnings.append(f"Multiple installations found across sources: {sources_str}")

        # Sort default by Name ascending
        all_records.sort(key=lambda x: x.name.lower())

        snapshot = InventorySnapshot(
            records=all_records,
            provider_capabilities=caps_dict,
            provider_errors=provider_errors,
            scan_timestamp=start_time,
        )
        self._last_snapshot = snapshot

        if progress_callback:
            progress_callback(f"Scan complete. Discovered {len(all_records)} applications.", 1.0)

        return snapshot

    def query(
        self,
        category: FilterCategory = FilterCategory.ALL,
        search_query: str = "",
        sort_by: str = "name",
        sort_ascending: bool = True,
    ) -> list[InstallationRecord]:
        """Filter and sort the current inventory."""
        if not self._last_snapshot:
            return []

        filtered = [
            r for r in self._last_snapshot.records
            if r.matches_filter(category) and r.matches_search(search_query)
        ]

        if sort_by == "name":
            filtered.sort(key=lambda r: r.name.lower(), reverse=not sort_ascending)
        elif sort_by == "source":
            filtered.sort(key=lambda r: (r.source.value, r.name.lower()), reverse=not sort_ascending)
        elif sort_by == "scope":
            filtered.sort(key=lambda r: (r.scope.value, r.name.lower()), reverse=not sort_ascending)
        elif sort_by == "size":
            filtered.sort(
                key=lambda r: (r.installed_size_bytes is not None, r.installed_size_bytes or 0),
                reverse=not sort_ascending,
            )

        return filtered
