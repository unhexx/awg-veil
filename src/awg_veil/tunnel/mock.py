"""Mock tunnel backend for CI and dry-run mode."""

from __future__ import annotations

from awg_veil.tunnel.base import TunnelBackend, TunnelStatus


class MockBackend(TunnelBackend):
    """Simulate tunnel operations without root or awg-quick."""

    # Shared state so sequential CLI dry-run invocations see the same tunnels.
    _shared_active: dict[str, str] = {}

    def __init__(self) -> None:
        self._active = MockBackend._shared_active

    def up(self, interface: str, config_path: str) -> None:
        self._active[interface] = config_path

    def down(self, interface: str) -> None:
        if interface not in self._active:
            msg = f"Interface {interface} is not up"
            raise RuntimeError(msg)
        del self._active[interface]

    def status(self, interface: str | None = None) -> TunnelStatus:
        if interface:
            is_up = interface in self._active
            raw = f"interface: {interface}\n  listening port: 51820\n" if is_up else ""
            return TunnelStatus(interface=interface, is_up=is_up, raw_output=raw)
        lines = [f"interface: {name}" for name in self._active]
        return TunnelStatus(
            interface="all",
            is_up=bool(self._active),
            raw_output="\n".join(lines),
        )
