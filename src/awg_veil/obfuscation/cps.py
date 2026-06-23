"""CPS (Custom Protocol Signature) packet builder."""

from __future__ import annotations


class CPSBuilder:
    """Build CPS strings using AmneziaWG 2.0 tags."""

    def __init__(self) -> None:
        self._parts: list[str] = []

    def add_bytes(self, hex_data: str) -> CPSBuilder:
        normalized = hex_data.lower().removeprefix("0x")
        self._parts.append(f"<b 0x{normalized}>")
        return self

    def add_timestamp(self) -> CPSBuilder:
        self._parts.append("<t>")
        return self

    def add_random(self, length: int) -> CPSBuilder:
        self._parts.append(f"<r {length}>")
        return self

    def add_random_chars(self, length: int) -> CPSBuilder:
        self._parts.append(f"<rc {length}>")
        return self

    def add_random_digits(self, length: int) -> CPSBuilder:
        self._parts.append(f"<rd {length}>")
        return self

    def build(self) -> str:
        return "".join(self._parts)

    @staticmethod
    def quic_initial_template() -> str:
        """Example QUIC-like CPS (for demonstration; do not copy verbatim in production)."""
        return (
            CPSBuilder()
            .add_bytes("c0ff000001")
            .add_bytes("08")
            .add_random_chars(8)
            .add_timestamp()
            .add_random(40)
            .build()
        )
