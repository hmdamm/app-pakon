#!/usr/bin/env python3
"""AppHarbor: Universal Linux Application Manager.

Main entry point.
"""

from __future__ import annotations

import logging
import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gio, Gtk, Adw

from appharbor import __app_id__
from appharbor.inventory.orchestrator import InventoryOrchestrator
from appharbor.ui.window import AppHarborWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("appharbor")


class AppHarborApplication(Adw.Application):
    """Core Libadwaita Application."""

    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_activate(self) -> None:
        window = self.props.active_window
        if not window:
            orchestrator = InventoryOrchestrator()
            window = AppHarborWindow(app=self, orchestrator=orchestrator)
        window.present()


def main() -> int:
    app = AppHarborApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
