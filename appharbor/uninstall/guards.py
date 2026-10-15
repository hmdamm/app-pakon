"""Critical system component guard to prevent catastrophic removal."""

from __future__ import annotations

import re

# Core system packages across Fedora/RHEL, Debian/Ubuntu, Arch, and openSUSE
CRITICAL_PACKAGE_PATTERNS = [
    # Kernel & boot
    r"^kernel(-.*)?$",
    r"^linux(-.*)?$",
    r"^vmlinuz(-.*)?$",
    r"^grub.*$",
    r"^shim.*$",
    r"^systemd(-.*)?$",
    r"^basesystem$",
    r"^coreutils(-.*)?$",
    r"^glibc(-.*)?$",
    r"^libc[0-9].*$",
    r"^bash$",
    r"^shadow-utils$",
    r"^util-linux(-.*)?$",
    # Package management
    r"^rpm(-.*)?$",
    r"^dnf[0-9]?(-.*)?$",
    r"^yum(-.*)?$",
    r"^apt(-.*)?$",
    r"^dpkg(-.*)?$",
    r"^pacman(-.*)?$",
    r"^zypper(-.*)?$",
    # Security & Elevation
    r"^polkit(-.*)?$",
    r"^sudo$",
    r"^pam(-.*)?$",
    r"^selinux(-.*)?$",
    # Core display & desktop shell
    r"^gnome-shell(-.*)?$",
    r"^mutter(-.*)?$",
    r"^plasma-desktop(-.*)?$",
    r"^kwin.*$",
    r"^sway.*$",
    r"^xorg-x11.*$",
    r"^wayland.*$",
    r"^NetworkManager(-.*)?$",
]

COMPILED_CRITICAL_PATTERNS = [re.compile(p, re.IGNORECASE) for p in CRITICAL_PACKAGE_PATTERNS]


def is_critical_package(package_id: str) -> bool:
    """Check if a package identifier corresponds to a protected core OS component."""
    if not package_id:
        return False
    clean_id = package_id.strip().lower()
    return any(pat.match(clean_id) for pat in COMPILED_CRITICAL_PATTERNS)
