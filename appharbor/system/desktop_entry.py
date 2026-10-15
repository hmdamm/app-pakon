"""FreeDesktop .desktop entry parsing utilities."""

from __future__ import annotations

import configparser
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class DesktopEntry:
    """Parsed FreeDesktop .desktop entry."""
    file_path: str
    name: str
    exec_cmd: Optional[str] = None
    icon: Optional[str] = None
    comment: Optional[str] = None
    categories: list[str] = field(default_factory=list)
    no_display: bool = False
    hidden: bool = False
    terminal: bool = False
    entry_type: str = "Application"
    raw_fields: dict[str, str] = field(default_factory=dict)

    @property
    def is_visible_app(self) -> bool:
        """Determines if the entry is an interactive user-facing application."""
        return (
            self.entry_type == "Application"
            and not self.no_display
            and not self.hidden
            and bool(self.name)
        )

    @property
    def clean_exec(self) -> Optional[str]:
        """Strips FreeDesktop field codes (%u, %f, %F, %U, etc.) from the Exec string."""
        if not self.exec_cmd:
            return None
        # Replace %f, %F, %u, %U, %d, %D, %n, %N, %i, %c, %k, %v, %m
        cleaned = re.sub(r"%\w", "", self.exec_cmd)
        return re.sub(r"\s+", " ", cleaned).strip()


def parse_desktop_file(file_path: Path | str) -> Optional[DesktopEntry]:
    """Parse a single .desktop file safely without executing anything."""
    path = Path(file_path)
    if not path.is_file():
        return None

    try:
        # Desktop files can contain comments, localized names [ru], [es], etc.
        # Use RawConfigParser with strict=False
        config = configparser.RawConfigParser(strict=False, interpolation=None)
        # Read with UTF-8 and replace errors
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            config.read_file(f)

        if not config.has_section("Desktop Entry"):
            return None

        section = config["Desktop Entry"]
        entry_type = section.get("Type", "Application")
        name = section.get("Name", path.stem)
        exec_cmd = section.get("Exec", None)
        icon = section.get("Icon", None)
        comment = section.get("Comment", None)
        categories_str = section.get("Categories", "")
        categories = [c.strip() for c in categories_str.split(";") if c.strip()]
        no_display = section.get("NoDisplay", "false").lower() == "true"
        hidden = section.get("Hidden", "false").lower() == "true"
        terminal = section.get("Terminal", "false").lower() == "true"

        return DesktopEntry(
            file_path=str(path.resolve()),
            name=name,
            exec_cmd=exec_cmd,
            icon=icon,
            comment=comment,
            categories=categories,
            no_display=no_display,
            hidden=hidden,
            terminal=terminal,
            entry_type=entry_type,
            raw_fields=dict(section),
        )
    except Exception:
        return None


def get_desktop_search_paths() -> dict[str, list[Path]]:
    """Return categorized standard search paths for desktop entries."""
    home = Path.home()
    user_paths = [
        home / ".local" / "share" / "applications",
    ]
    system_paths = [
        Path("/usr/local/share/applications"),
        Path("/usr/share/applications"),
    ]

    # Additional standard integration dirs if they exist
    flatpak_system = Path("/var/lib/flatpak/exports/share/applications")
    if flatpak_system.exists():
        system_paths.append(flatpak_system)

    flatpak_user = home / ".local" / "share" / "flatpak" / "exports" / "share" / "applications"
    if flatpak_user.exists():
        user_paths.append(flatpak_user)

    snap_desktop = Path("/var/lib/snapd/desktop/applications")
    if snap_desktop.exists():
        system_paths.append(snap_desktop)

    return {
        "user": [p for p in user_paths if p.exists()],
        "system": [p for p in system_paths if p.exists()],
    }
