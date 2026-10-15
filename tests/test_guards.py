"""Unit tests for critical system package guards."""

from appharbor.uninstall.guards import is_critical_package


def test_critical_packages_are_blocked():
    critical_cases = [
        "kernel",
        "kernel-core",
        "linux",
        "systemd",
        "systemd-udev",
        "glibc",
        "libc6",
        "dnf",
        "dnf5",
        "rpm",
        "apt",
        "dpkg",
        "pacman",
        "zypper",
        "gnome-shell",
        "mutter",
        "coreutils",
        "polkit",
    ]
    for pkg in critical_cases:
        assert is_critical_package(pkg) is True, f"Expected {pkg} to be flagged as critical"


def test_safe_applications_are_not_blocked():
    safe_cases = [
        "firefox",
        "google-chrome-stable",
        "vlc",
        "gimp",
        "org.mozilla.firefox",
        "com.visualstudio.code",
        "discord",
        "spotify-client",
        "libreoffice",
    ]
    for pkg in safe_cases:
        assert is_critical_package(pkg) is False, f"Expected {pkg} to NOT be flagged as critical"
