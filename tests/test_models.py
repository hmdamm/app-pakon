"""Unit tests for domain models."""

import pytest
from appharbor.domain.models import (
    ConfidenceLevel,
    FilterCategory,
    InstallationRecord,
    ScopeEnum,
    SourceEnum,
)


def test_installation_record_filter_matching():
    # Test Flatpak System record
    rec_flatpak_sys = InstallationRecord(
        id="flatpak:system:org.mozilla.firefox",
        name="Firefox",
        package_id="org.mozilla.firefox",
        source=SourceEnum.FLATPAK,
        scope=ScopeEnum.SYSTEM,
    )
    # Should match ALL, FLATPAK, and SYSTEM
    assert rec_flatpak_sys.matches_filter(FilterCategory.ALL) is True
    assert rec_flatpak_sys.matches_filter(FilterCategory.FLATPAK) is True
    assert rec_flatpak_sys.matches_filter(FilterCategory.SYSTEM) is True
    assert rec_flatpak_sys.matches_filter(FilterCategory.USER) is False
    assert rec_flatpak_sys.matches_filter(FilterCategory.SNAP) is False
    assert rec_flatpak_sys.matches_filter(FilterCategory.UNKNOWN) is False

    # Test AppImage User record
    rec_appimage_user = InstallationRecord(
        id="appimage:user:my-app",
        name="My App",
        package_id="my-app",
        source=SourceEnum.APPIMAGE,
        scope=ScopeEnum.USER,
    )
    assert rec_appimage_user.matches_filter(FilterCategory.ALL) is True
    assert rec_appimage_user.matches_filter(FilterCategory.APPIMAGE) is True
    assert rec_appimage_user.matches_filter(FilterCategory.USER) is True
    assert rec_appimage_user.matches_filter(FilterCategory.SYSTEM) is False

    # Test Unknown record
    rec_unknown = InstallationRecord(
        id="manual:user:custom",
        name="Custom Script",
        package_id="custom",
        source=SourceEnum.UNKNOWN,
        scope=ScopeEnum.USER,
    )
    assert rec_unknown.matches_filter(FilterCategory.UNKNOWN) is True
    assert rec_unknown.matches_filter(FilterCategory.USER) is True
    assert rec_unknown.matches_filter(FilterCategory.SYSTEM) is False


def test_installation_record_search():
    rec = InstallationRecord(
        id="rpm:system:code",
        name="Visual Studio Code",
        package_id="code",
        source=SourceEnum.RPM,
        scope=ScopeEnum.SYSTEM,
        version="1.85.0",
        description="Code editing redefined",
    )
    assert rec.matches_search("visual") is True
    assert rec.matches_search("CODE") is True
    assert rec.matches_search("1.85") is True
    assert rec.matches_search("redefined") is True
    assert rec.matches_search("nonexistent") is False
    assert rec.matches_search("") is True
