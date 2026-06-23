"""Abstract tunnel backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TunnelStatus:
    interface: str
    is_up: bool
    raw_output: str = ""
    peers: list[dict[str, str]] = field(default_factory=list)


class TunnelBackend(ABC):
    """Platform-specific tunnel operations."""

    @abstractmethod
    def up(self, interface: str, config_path: str) -> None:
        """Bring tunnel up."""

    @abstractmethod
    def down(self, interface: str) -> None:
        """Bring tunnel down."""

    @abstractmethod
    def status(self, interface: str | None = None) -> TunnelStatus:
        """Query tunnel status."""
