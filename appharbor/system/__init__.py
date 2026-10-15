"""System utilities and process execution."""

from appharbor.system.capabilities import OsInfo, detect_os, format_bytes, get_elevation_tool, has_command
from appharbor.system.desktop_entry import DesktopEntry, get_desktop_search_paths, parse_desktop_file
from appharbor.system.process import ProcessResult, is_binary_available, run_command_safely

__all__ = [
    "DesktopEntry",
    "OsInfo",
    "ProcessResult",
    "detect_os",
    "format_bytes",
    "get_desktop_search_paths",
    "get_elevation_tool",
    "has_command",
    "is_binary_available",
    "parse_desktop_file",
    "run_command_safely",
]
