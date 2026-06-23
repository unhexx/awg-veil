"""Pydantic models for AmneziaWG configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from awg_veil.config.validator import ValidationResult


class ObfuscationConfig(BaseModel):
    """AmneziaWG 2.0 obfuscation parameters."""

    h1: str | None = None
    h2: str | None = None
    h3: str | None = None
    h4: str | None = None
    s1: int | None = None
    s2: int | None = None
    s3: int | None = None
    s4: int | None = None
    jc: int | None = None
    jmin: int | None = None
    jmax: int | None = None
    i1: str | None = None
    i2: str | None = None
    i3: str | None = None
    i4: str | None = None
    i5: str | None = None

    def is_empty(self) -> bool:
        return all(
            getattr(self, field) is None
            for field in (
                "h1", "h2", "h3", "h4",
                "s1", "s2", "s3", "s4",
                "jc", "jmin", "jmax",
                "i1", "i2", "i3", "i4", "i5",
            )
        )

    def to_interface_fields(self) -> dict[str, str]:
        """Convert obfuscation fields to awg-quick [Interface] key names."""
        mapping = {
            "h1": "H1", "h2": "H2", "h3": "H3", "h4": "H4",
            "s1": "S1", "s2": "S2", "s3": "S3", "s4": "S4",
            "jc": "Jc", "jmin": "Jmin", "jmax": "Jmax",
            "i1": "I1", "i2": "I2", "i3": "I3", "i4": "I4", "i5": "I5",
        }
        result: dict[str, str] = {}
        for attr, key in mapping.items():
            value = getattr(self, attr)
            if value is not None:
                result[key] = str(value) if not isinstance(value, str) else value
        return result

    @classmethod
    def from_interface_fields(cls, fields: dict[str, str]) -> ObfuscationConfig:
        """Build from [Interface] or [AmneziaWG] section keys."""
        key_map = {
            "H1": "h1", "H2": "h2", "H3": "h3", "H4": "h4",
            "S1": "s1", "S2": "s2", "S3": "s3", "S4": "s4",
            "JC": "jc", "Jc": "jc",
            "JMIN": "jmin", "Jmin": "jmin",
            "JMAX": "jmax", "Jmax": "jmax",
            "I1": "i1", "I2": "i2", "I3": "i3", "I4": "i4", "I5": "i5",
        }
        int_fields = {"s1", "s2", "s3", "s4", "jc", "jmin", "jmax"}
        data: dict[str, str | int] = {}
        for key, value in fields.items():
            attr = key_map.get(key)
            if attr is None:
                continue
            if attr in int_fields:
                data[attr] = int(value)
            else:
                data[attr] = value
        return cls(**data)  # type: ignore[arg-type]


class InterfaceConfig(BaseModel):
    """WireGuard [Interface] section."""

    private_key: str | None = None
    address: list[str] = Field(default_factory=list)
    listen_port: int | None = None
    dns: list[str] = Field(default_factory=list)
    mtu: int | None = None
    extra: dict[str, str] = Field(default_factory=dict)

    def all_fields(self) -> dict[str, str]:
        result: dict[str, str] = {}
        if self.private_key:
            result["PrivateKey"] = self.private_key
        if self.address:
            result["Address"] = ", ".join(self.address)
        if self.listen_port is not None:
            result["ListenPort"] = str(self.listen_port)
        if self.dns:
            result["DNS"] = ", ".join(self.dns)
        if self.mtu is not None:
            result["MTU"] = str(self.mtu)
        result.update(self.extra)
        return result


class PeerConfig(BaseModel):
    """WireGuard [Peer] section."""

    public_key: str | None = None
    endpoint: str | None = None
    allowed_ips: list[str] = Field(default_factory=list)
    persistent_keepalive: int | None = None
    preshared_key: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)

    def all_fields(self) -> dict[str, str]:
        result: dict[str, str] = {}
        if self.public_key:
            result["PublicKey"] = self.public_key
        if self.endpoint:
            result["Endpoint"] = self.endpoint
        if self.allowed_ips:
            result["AllowedIPs"] = ", ".join(self.allowed_ips)
        if self.persistent_keepalive is not None:
            result["PersistentKeepalive"] = str(self.persistent_keepalive)
        if self.preshared_key:
            result["PresharedKey"] = self.preshared_key
        result.update(self.extra)
        return result


class AmneziaConfig(BaseModel):
    """Complete AmneziaWG configuration."""

    interface: InterfaceConfig = Field(default_factory=InterfaceConfig)
    peers: list[PeerConfig] = Field(default_factory=list)
    obfuscation: ObfuscationConfig = Field(default_factory=ObfuscationConfig)

    @classmethod
    def from_file(cls, path: str) -> AmneziaConfig:
        from awg_veil.config.parser import load_config

        return load_config(path)

    def to_file(self, path: str, *, awg_quick: bool = True) -> None:
        from awg_veil.config.parser import save_config

        save_config(self, path, awg_quick=awg_quick)

    def check(self) -> ValidationResult:
        """Validate AmneziaWG rules (not to be confused with Pydantic's validate)."""
        from awg_veil.config.validator import validate_config

        return validate_config(self)
