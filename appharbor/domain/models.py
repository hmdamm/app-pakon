"""Domain models for AppHarbor."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SourceEnum(str, Enum):
    """Packaging mechanism or installation source."""
    FLATPAK = "Flatpak"
    SNAP = "Snap"
    APPIMAGE = "AppImage"
    RPM = "RPM"
    DEB = "DEB/APT"
    PACMAN = "Pacman"
    ZYPPER = "Zypper"
    MANUAL = "Manual"
    UNKNOWN = "Unknown"


class ScopeEnum(str, Enum):
    """Scope of installation."""
    SYSTEM = "System"
    USER = "User"
    UNKNOWN = "Unknown"


class ConfidenceLevel(str, Enum):
    """Confidence level of detection provenance."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class FilterCategory(str, Enum):
    """Primary inventory filters requested in requirement specification."""
    ALL = "All"
    FLATPAK = "Flatpak"
    SNAP = "Snap"
    APPIMAGE = "AppImage"
    SYSTEM = "System"
    USER = "User"
    UNKNOWN = "Unknown"


@dataclass
class InstallationRecord:
    """Represents a discovered application installation."""
    id: str
    name: str
    package_id: str
    source: SourceEnum
    scope: ScopeEnum
    version: Optional[str] = None
    architecture: Optional[str] = None
    origin: Optional[str] = None
    exec_target: Optional[str] = None
    desktop_entry_path: Optional[str] = None
    icon_name_or_path: Optional[str] = None
    install_path: Optional[str] = None
    installed_size_bytes: Optional[int] = None
    install_date: Optional[str] = None
    requires_elevation: bool = False
    is_removable: bool = True
    is_critical_system_package: bool = False
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    description: Optional[str] = None
    known_data_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def matches_filter(self, category: FilterCategory) -> bool:
        """Check if this record matches an inventory filter category.
        
        Note that filters intentionally overlap:
        e.g., a system Flatpak matches both FLATPAK and SYSTEM.
        """
        if category == FilterCategory.ALL:
            return True
        elif category == FilterCategory.FLATPAK:
            return self.source == SourceEnum.FLATPAK
        elif category == FilterCategory.SNAP:
            return self.source == SourceEnum.SNAP
        elif category == FilterCategory.APPIMAGE:
            return self.source == SourceEnum.APPIMAGE
        elif category == FilterCategory.SYSTEM:
            return self.scope == ScopeEnum.SYSTEM
        elif category == FilterCategory.USER:
            return self.scope == ScopeEnum.USER
        elif category == FilterCategory.UNKNOWN:
            return self.source == SourceEnum.UNKNOWN or self.scope == ScopeEnum.UNKNOWN
        return False

    def matches_search(self, query: str) -> bool:
        """Case-insensitive search over name, package_id, and description."""
        if not query:
            return True
        q = query.strip().lower()
        targets = [
            self.name.lower(),
            self.package_id.lower(),
            (self.version or "").lower(),
            (self.description or "").lower(),
            (self.exec_target or "").lower(),
        ]
        return any(q in target for target in targets)


@dataclass
class ProviderCapabilities:
    """Reports what a specific package provider supports."""
    provider_id: str
    is_available: bool
    version_string: Optional[str] = None
    can_inventory: bool = True
    can_uninstall: bool = False
    can_detect_size: bool = False
    can_detect_user_data: bool = False
    default_elevation_required: bool = False
    status_message: str = "Ready"


@dataclass
class UninstallPlan:
    """Safe, explicit uninstallation plan prepared before asking for confirmation."""
    record: InstallationRecord
    target_summary: str
    commands_to_run: list[list[str]]
    requires_elevation: bool
    paths_to_delete: list[str] = field(default_factory=list)
    preserve_user_data: bool = True
    user_data_paths: list[str] = field(default_factory=list)
    consequences_summary: str = ""
    is_critical_warning: bool = False
    is_executable: bool = True
    error_message: Optional[str] = None


@dataclass
class OperationResult:
    """Structured result of an uninstallation or scan operation."""
    success: bool
    target_id: str
    message: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    warnings: list[str] = field(default_factory=list)
