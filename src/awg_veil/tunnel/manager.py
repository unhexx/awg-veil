"""High-level tunnel manager."""

from __future__ import annotations

import os

from awg_veil.tunnel.base import TunnelBackend, TunnelStatus
from awg_veil.tunnel.linux import LinuxBackend
from awg_veil.tunnel.mock import MockBackend


class TunnelManager:
    """Manage AmneziaWG tunnel lifecycle."""

    def __init__(self, interface: str, backend: TunnelBackend | None = None) -> None:
        self.interface = interface
        self._backend = backend or _default_backend()

    def up(self, config_path: str) -> None:
        self._backend.up(self.interface, config_path)

    def down(self) -> None:
        self._backend.down(self.interface)

    def status(self) -> TunnelStatus:
        return self._backend.status(self.interface)


def _default_backend() -> TunnelBackend:
    if os.environ.get("AWG_VEIL_MOCK", "").lower() in ("1", "true", "yes"):
        return MockBackend()
    return LinuxBackend()
