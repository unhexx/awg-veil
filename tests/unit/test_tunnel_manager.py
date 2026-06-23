"""Tests for tunnel manager defaults."""

from __future__ import annotations

from awg_veil.tunnel.linux import LinuxBackend
from awg_veil.tunnel.manager import TunnelManager, _default_backend
from awg_veil.tunnel.mock import MockBackend


def test_default_backend_mock(monkeypatch) -> None:
    monkeypatch.setenv("AWG_VEIL_MOCK", "1")
    assert isinstance(_default_backend(), MockBackend)

def test_default_backend_linux(monkeypatch) -> None:
    monkeypatch.delenv("AWG_VEIL_MOCK", raising=False)
    assert isinstance(_default_backend(), LinuxBackend)

def test_manager_delegates() -> None:
    backend = MockBackend()
    mgr = TunnelManager("awg0", backend=backend)
    mgr.up("/tmp/x.conf")
    assert mgr.status().is_up
