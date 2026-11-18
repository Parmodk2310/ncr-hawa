"""Pytest configuration and global fixtures."""

from __future__ import annotations

import socket

import pytest


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Block real network sockets during tests to guarantee zero live calls."""

    def guarded_socket(*args: object, **kwargs: object) -> None:
        raise RuntimeError("Real network access is blocked in tests!")

    monkeypatch.setattr(socket, "socket", guarded_socket)
