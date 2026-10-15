"""Host environment and capability detection."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class OsInfo:
    """Information about the host Linux distribution."""
    id: str
    name: str
    version_id: str
    pretty_name: str
    id_like: list[str]


def detect_os() -> OsInfo:
    """Parse /etc/os-release safely to identify the distribution."""
    os_release = Path("/etc/os-release")
    data = {}
    if os_release.exists():
        try:
            with open(os_release, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    v = v.strip("\"'")
                    data[k.strip()] = v
        except Exception:
            pass

    os_id = data.get("ID", "linux").lower()
    name = data.get("NAME", "Linux")
    version_id = data.get("VERSION_ID", "")
    pretty_name = data.get("PRETTY_NAME", f"{name} {version_id}".strip())
    id_like_str = data.get("ID_LIKE", "")
    id_like = [x.strip().lower() for x in id_like_str.split() if x.strip()]

    return OsInfo(
        id=os_id,
        name=name,
        version_id=version_id,
        pretty_name=pretty_name,
        id_like=id_like,
    )


def has_command(cmd: str) -> bool:
    """Check if a command exists in system PATH."""
    return shutil.which(cmd) is not None


def get_elevation_tool() -> Optional[str]:
    """Check for graphical or polkit elevation tool."""
    for tool in ["pkexec", "sudo"]:
        if has_command(tool):
            return tool
    return None


def format_bytes(num_bytes: Optional[int]) -> str:
    """Format bytes into a human-readable string (e.g. 45.2 MB)."""
    if num_bytes is None:
        return "Unknown"
    if num_bytes < 1024:
        return f"{num_bytes} B"
    for unit in ["KB", "MB", "GB", "TB"]:
        num_bytes /= 1024.0
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
    return f"{num_bytes:.1f} PB"
