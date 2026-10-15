"""Unit tests for desktop entry parsing."""

import tempfile
from pathlib import Path
from appharbor.system.desktop_entry import parse_desktop_file


def test_parse_valid_desktop_file():
    content = """[Desktop Entry]
Name=Super Calculator
Type=Application
Exec=super-calc %u --some-flag
Icon=accessories-calculator
Comment=Perform arithmetic
Categories=Utility;Science;
NoDisplay=false
"""
    with tempfile.NamedTemporaryFile("w", suffix=".desktop", delete=False) as tf:
        tf.write(content)
        tf_path = tf.name

    try:
        entry = parse_desktop_file(tf_path)
        assert entry is not None
        assert entry.name == "Super Calculator"
        assert entry.is_visible_app is True
        assert entry.clean_exec == "super-calc --some-flag"
        assert entry.icon == "accessories-calculator"
        assert "Utility" in entry.categories
    finally:
        Path(tf_path).unlink()


def test_parse_hidden_desktop_file():
    content = """[Desktop Entry]
Name=Background Helper
Type=Application
Exec=helper
NoDisplay=true
"""
    with tempfile.NamedTemporaryFile("w", suffix=".desktop", delete=False) as tf:
        tf.write(content)
        tf_path = tf.name

    try:
        entry = parse_desktop_file(tf_path)
        assert entry is not None
        assert entry.no_display is True
        assert entry.is_visible_app is False
    finally:
        Path(tf_path).unlink()
