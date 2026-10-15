"""Unit tests for package provider adapters."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from appharbor.domain.models import (
    ConfidenceLevel,
    InstallationRecord,
    ScopeEnum,
    SourceEnum,
)
from appharbor.providers.appimage import AppImageProvider, parse_appimage_filename
from appharbor.providers.flatpak import FlatpakProvider, _parse_size_string
from appharbor.providers.rpm_dnf import RpmDnfProvider
from appharbor.system.process import ProcessResult


def test_flatpak_size_parsing():
    assert _parse_size_string("18.9 MB") == 189 * (1024**2) // 10
    assert _parse_size_string("1.2 GB") == int(1.2 * (1024**3))
    assert _parse_size_string("500 KB") == 500 * 1024
    assert _parse_size_string("-") is None
    assert _parse_size_string(None) is None


def test_flatpak_scan_mock():
    mock_stdout = (
        "org.mozilla.firefox\tFirefox\t120.0\tstable\tx86_64\tflathub\tsystem\t240.5 MB\tWeb browser\torg.mozilla.firefox/x86_64/stable\n"
        "com.spotify.Client\tSpotify\t1.2.0\tstable\tx86_64\tflathub\tuser\t150.0 MB\tMusic player\tcom.spotify.Client/x86_64/stable\n"
    )
    provider = FlatpakProvider()

    with patch.object(provider, "detect_capabilities") as mock_caps:
        mock_caps.return_value.is_available = True
        with patch("appharbor.providers.flatpak.run_command_safely") as mock_run:
            mock_run.return_value = ProcessResult(exit_code=0, stdout=mock_stdout, stderr="")
            records = provider.scan_applications()

    assert len(records) == 2
    firefox = records[0]
    assert firefox.name == "Firefox"
    assert firefox.package_id == "org.mozilla.firefox"
    assert firefox.scope == ScopeEnum.SYSTEM
    assert firefox.source == SourceEnum.FLATPAK
    assert firefox.version == "120.0"

    spotify = records[1]
    assert spotify.name == "Spotify"
    assert spotify.scope == ScopeEnum.USER
    assert spotify.source == SourceEnum.FLATPAK


def test_flatpak_uninstall_plan_data_preservation():
    provider = FlatpakProvider()
    record = InstallationRecord(
        id="flatpak:user:org.test.App",
        name="Test App",
        package_id="org.test.App",
        source=SourceEnum.FLATPAK,
        scope=ScopeEnum.USER,
    )
    # With keep_data=True
    plan_keep = provider.plan_uninstall(record, keep_data=True)
    assert plan_keep.is_executable is True
    assert "--delete-data" not in plan_keep.commands_to_run[0]
    assert "--user" in plan_keep.commands_to_run[0]

    # With keep_data=False
    plan_delete = provider.plan_uninstall(record, keep_data=False)
    assert plan_delete.is_executable is True
    assert "--delete-data" in plan_delete.commands_to_run[0]


def test_appimage_filename_parsing():
    name, ver = parse_appimage_filename("Krita-5.2.2-x86_64.AppImage")
    assert "Krita" in name
    assert ver == "5.2.2"

    name, ver = parse_appimage_filename("30nama-1.4.3.AppImage")
    assert "30nama" in name.lower()
    assert ver == "1.4.3"

    name, ver = parse_appimage_filename("SimpleTool.AppImage")
    assert "Simpletool" in name
    assert ver is None


def test_rpm_critical_package_uninstall_plan():
    provider = RpmDnfProvider()
    record = InstallationRecord(
        id="rpm:system:systemd",
        name="systemd",
        package_id="systemd",
        source=SourceEnum.RPM,
        scope=ScopeEnum.SYSTEM,
        is_critical_system_package=True,
    )
    plan = provider.plan_uninstall(record)
    assert plan.is_executable is False
    assert plan.is_critical_warning is True
    assert "critical operating system component" in plan.error_message
