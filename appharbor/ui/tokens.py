"""GNOME HIG styling helpers and Libadwaita integration."""

from __future__ import annotations

import logging
from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gdk, Gtk

logger = logging.getLogger(__name__)


def load_custom_css() -> None:
    """Load minimal structural stylesheet for Libadwaita."""
    css_path = Path(__file__).parent / "style.css"
    if not css_path.exists():
        return

    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(str(css_path))
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
    except Exception as exc:
        logger.warning("Failed to load minimal CSS: %s", exc)
