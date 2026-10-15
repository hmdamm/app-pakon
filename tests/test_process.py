"""Unit tests for safe process execution."""

import sys
import pytest
from appharbor.system.process import run_command_safely, is_binary_available


def test_is_binary_available():
    assert is_binary_available("python3") is True
    assert is_binary_available("totally_non_existent_binary_xyz_123") is False


def test_safe_execution_success():
    res = run_command_safely([sys.executable, "-c", "print('hello from test')"])
    assert res.is_success is True
    assert res.exit_code == 0
    assert "hello from test" in res.stdout
    assert res.was_timeout is False


def test_safe_execution_exit_code():
    res = run_command_safely([sys.executable, "-c", "import sys; sys.exit(42)"])
    assert res.is_success is False
    assert res.exit_code == 42


def test_safe_execution_timeout():
    res = run_command_safely(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        timeout_seconds=0.5,
    )
    assert res.is_success is False
    assert res.was_timeout is True
    assert "timed out" in res.stderr.lower()


def test_missing_binary():
    res = run_command_safely(["completely_imaginary_tool_404", "--help"])
    assert res.is_success is False
    assert res.exit_code == 127
    assert "not found" in res.stderr
