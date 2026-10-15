"""Uninstall service and safety guards."""

from appharbor.uninstall.guards import is_critical_package
from appharbor.uninstall.service import UninstallService

__all__ = ["UninstallService", "is_critical_package"]
