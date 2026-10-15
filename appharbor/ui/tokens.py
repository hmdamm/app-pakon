"""UI design tokens and CSS provider loader."""

from __future__ import annotations

import logging
from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gdk, Gtk

logger = logging.getLogger(__name__)


def load_custom_css() -> None:
    """Load and register the custom warm graphite/ivory stylesheet."""
    css_path = Path(__file__).parent / "style.css"
    if not css_path.exists():
        logger.warning("style.css not found at %s", css_path)
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
            logger.info("Custom CSS loaded successfully.")
    except Exception as exc:
        logger.error("Failed to load custom CSS: %s", exc)


def create_chip(label: str, style_class: str) -> Gtk.Label:
    """Create a styled metadata badge with accessible text."""
    lbl = Gtk.Label(label=label)
    lbl.add_css_class("chip")
    lbl.add_css_class(style_class)
    return lbl
