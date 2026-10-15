"""Package providers for AppHarbor."""

from appharbor.providers.appimage import AppImageProvider
from appharbor.providers.base import BaseProvider
from appharbor.providers.dpkg_apt import DpkgAptProvider
from appharbor.providers.flatpak import FlatpakProvider
from appharbor.providers.manual_desktop import ManualDesktopProvider
from appharbor.providers.pacman import PacmanProvider
from appharbor.providers.rpm_dnf import RpmDnfProvider
from appharbor.providers.snap import SnapProvider
from appharbor.providers.zypper import ZypperProvider

__all__ = [
    "AppImageProvider",
    "BaseProvider",
    "DpkgAptProvider",
    "FlatpakProvider",
    "ManualDesktopProvider",
    "PacmanProvider",
    "RpmDnfProvider",
    "SnapProvider",
    "ZypperProvider",
]
