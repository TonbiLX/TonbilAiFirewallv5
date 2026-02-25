"""
Shared pytest configuration and fixtures for TonbilAI firewall tests.

This conftest.py serves the entire tests/ package. It provides:
- A reusable factory for building AsyncMock subprocess objects so individual
  test modules do not have to repeat the same boilerplate.
- The asyncio_mode is set to "auto" via pytest.ini / pyproject.toml; the
  fixture is kept here so future tests can also use it.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helper: build a fake asyncio subprocess process
# ---------------------------------------------------------------------------

def make_proc(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> AsyncMock:
    """Return an AsyncMock that behaves like an asyncio.subprocess.Process.

    Parameters
    ----------
    stdout:
        Raw bytes that the process "writes" to its stdout pipe.
    stderr:
        Raw bytes that the process "writes" to its stderr pipe.
    returncode:
        Exit code of the fake process.

    The returned mock exposes:
    - ``communicate()`` — coroutine that returns (stdout, stderr)
    - ``returncode``    — int attribute
    - ``stdin``         — MagicMock (write / close accepted silently)
    """
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    proc.stdin = MagicMock()
    proc.stdin.write = MagicMock()
    proc.stdin.close = MagicMock()
    return proc
