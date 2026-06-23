"""Integration tests for mock tunnel backend."""

from __future__ import annotations

import pytest

from awg_veil.tunnel.manager import TunnelManager
from awg_veil.tunnel.mock import MockBackend


def test_mock_up_down() -> None:
    backend = MockBackend()
    mgr = TunnelManager("awg0", backend=backend)
    mgr.up("/tmp/test.conf")
    st = mgr.status()
    assert st.is_up
    mgr.down()
    st = mgr.status()
    assert not st.is_up

def test_mock_down_not_up() -> None:
    backend = MockBackend()
    mgr = TunnelManager("awg0", backend=backend)
    with pytest.raises(RuntimeError, match="not up"):
        mgr.down()
