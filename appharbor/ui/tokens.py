"""GNOME HIG styling helpers and Libadwaita integration."""

from __future__ import annotations

import logging
from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gdk, Gtk

from appharbor.domain.models import ScopeEnum, SourceEnum

logger = logging.getLogger(__name__)


def load_custom_css() -> None:
    """Load minimal semantic badges stylesheet for Libadwaita."""
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


def create_source_badge(source: SourceEnum) -> Gtk.Label:
    """Create a semantic Libadwaita badge for application source packaging."""
    lbl = Gtk.Label(label=source.value)
    lbl.add_css_class("badge-pill")
    mapping = {
        SourceEnum.FLATPAK: "badge-flatpak",
        SourceEnum.RPM: "badge-rpm",
        SourceEnum.SNAP: "badge-snap",
        SourceEnum.APPIMAGE: "badge-appimage",
        SourceEnum.DEB: "badge-deb",
        SourceEnum.MANUAL: "badge-manual",
        SourceEnum.UNKNOWN: "badge-unknown",
    }
    lbl.add_css_class(mapping.get(source, "badge-unknown"))
    return lbl


def create_scope_badge(scope: ScopeEnum) -> Gtk.Label:
    """Create a semantic Libadwaita badge for user vs system scope."""
    lbl = Gtk.Label(label=scope.value)
    lbl.add_css_class("badge-pill")
    if scope == ScopeEnum.USER:
        lbl.add_css_class("badge-user")
    else:
        lbl.add_css_class("badge-system")
    return lbl
