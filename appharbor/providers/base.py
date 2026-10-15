"""Base interface for application providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional

from appharbor.domain.models import (
    InstallationRecord,
    OperationResult,
    ProviderCapabilities,
    UninstallPlan,
)


class BaseProvider(ABC):
    """Abstract provider adapter for a packaging mechanism or discovery source."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique machine identifier for the provider (e.g. 'flatpak', 'rpm_dnf')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable provider label (e.g. 'Flatpak', 'RPM / DNF')."""
        pass

    @abstractmethod
    def detect_capabilities(self) -> ProviderCapabilities:
        """Probe the system to determine if this provider is available and what it supports."""
        pass

    @abstractmethod
    def scan_applications(
        self,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> list[InstallationRecord]:
        """Discover installed applications belonging to this provider."""
        pass

    @abstractmethod
    def plan_uninstall(
        self,
        record: InstallationRecord,
        keep_data: bool = True,
    ) -> UninstallPlan:
        """Construct a safe, structured uninstallation plan without executing it."""
        pass

    @abstractmethod
    def execute_uninstall(
        self,
        plan: UninstallPlan,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> OperationResult:
        """Execute the confirmed uninstallation plan."""
        pass
