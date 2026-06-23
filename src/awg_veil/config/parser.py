"""INI parser for AmneziaWG configuration files."""

from __future__ import annotations

import configparser
import re
from pathlib import Path

from awg_veil.config.models import (
    AmneziaConfig,
    InterfaceConfig,
    ObfuscationConfig,
    PeerConfig,
)

# Keys that belong to obfuscation, not standard WireGuard interface
OBFUSCATION_KEYS = {
    "H1", "H2", "H3", "H4",
    "S1", "S2", "S3", "S4",
    "Jc", "JC", "Jmin", "JMIN", "Jmax", "JMAX",
    "I1", "I2", "I3", "I4", "I5",
}

INTERFACE_STANDARD_KEYS = {
    "PrivateKey", "Address", "ListenPort", "DNS", "MTU",
    "Table", "PreUp", "PostUp", "PreDown", "PostDown",
    "SaveConfig", "FwMark",
}

PEER_STANDARD_KEYS = {
    "PublicKey", "Endpoint", "AllowedIPs", "PersistentKeepalive", "PresharedKey",
}


def _split_list(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,;]", value) if part.strip()]


def _parse_interface_section(section: dict[str, str]) -> tuple[InterfaceConfig, ObfuscationConfig]:
    obf_fields: dict[str, str] = {}
    iface_fields: dict[str, str] = {}

    for key, value in section.items():
        # configparser lowercases keys; restore canonical casing
        canonical = _restore_key_case(key)
        if canonical in OBFUSCATION_KEYS:
            obf_fields[canonical] = value
        else:
            iface_fields[canonical] = value

    interface = InterfaceConfig(
        private_key=iface_fields.get("PrivateKey"),
        address=_split_list(iface_fields["Address"]) if "Address" in iface_fields else [],
        listen_port=int(iface_fields["ListenPort"]) if "ListenPort" in iface_fields else None,
        dns=_split_list(iface_fields["DNS"]) if "DNS" in iface_fields else [],
        mtu=int(iface_fields["MTU"]) if "MTU" in iface_fields else None,
        extra={
            k: v for k, v in iface_fields.items()
            if k not in INTERFACE_STANDARD_KEYS
        },
    )
    obfuscation = ObfuscationConfig.from_interface_fields(obf_fields)
    return interface, obfuscation


def _restore_key_case(key: str) -> str:
    """Map configparser lowercased keys back to WireGuard casing."""
    case_map = {
        "privatekey": "PrivateKey",
        "address": "Address",
        "listenport": "ListenPort",
        "dns": "DNS",
        "mtu": "MTU",
        "table": "Table",
        "preup": "PreUp",
        "postup": "PostUp",
        "predown": "PreDown",
        "postdown": "PostDown",
        "saveconfig": "SaveConfig",
        "fwmark": "FwMark",
        "publickey": "PublicKey",
        "endpoint": "Endpoint",
        "allowedips": "AllowedIPs",
        "persistentkeepalive": "PersistentKeepalive",
        "presharedkey": "PresharedKey",
        "h1": "H1", "h2": "H2", "h3": "H3", "h4": "H4",
        "s1": "S1", "s2": "S2", "s3": "S3", "s4": "S4",
        "jc": "Jc", "jmin": "Jmin", "jmax": "Jmax",
        "i1": "I1", "i2": "I2", "i3": "I3", "i4": "I4", "i5": "I5",
    }
    return case_map.get(key.lower(), key)


def _parse_peer_section(section: dict[str, str]) -> PeerConfig:
    fields = {_restore_key_case(k): v for k, v in section.items()}
    return PeerConfig(
        public_key=fields.get("PublicKey"),
        endpoint=fields.get("Endpoint"),
        allowed_ips=_split_list(fields["AllowedIPs"]) if "AllowedIPs" in fields else [],
        persistent_keepalive=(
            int(fields["PersistentKeepalive"]) if "PersistentKeepalive" in fields else None
        ),
        preshared_key=fields.get("PresharedKey"),
        extra={k: v for k, v in fields.items() if k not in PEER_STANDARD_KEYS},
    )


def load_config(path: str | Path) -> AmneziaConfig:
    """Load configuration from an awg*.conf file."""
    config_path = Path(path)
    parser = configparser.ConfigParser()
    parser.optionxform = lambda option: option  # type: ignore[method-assign, assignment]
    with config_path.open(encoding="utf-8") as fh:
        parser.read_file(fh)

    if "Interface" not in parser:
        msg = f"Missing [Interface] section in {config_path}"
        raise ValueError(msg)

    interface, obfuscation = _parse_interface_section(dict(parser["Interface"]))

    # Also read dedicated [AmneziaWG] section if present
    if "AmneziaWG" in parser:
        awg_obf = ObfuscationConfig.from_interface_fields(dict(parser["AmneziaWG"]))
        # Merge: [AmneziaWG] overrides interface-level obfuscation fields
        merged = obfuscation.model_dump()
        for key, value in awg_obf.model_dump().items():
            if value is not None:
                merged[key] = value
        obfuscation = ObfuscationConfig(**merged)

    peers = [_parse_peer_section(dict(parser[section])) for section in parser if section == "Peer"]

    return AmneziaConfig(interface=interface, peers=peers, obfuscation=obfuscation)


def _write_section(lines: list[str], name: str, fields: dict[str, str]) -> None:
    if not fields:
        return
    lines.append(f"[{name}]")
    for key, value in fields.items():
        lines.append(f"{key} = {value}")
    lines.append("")


def save_config(config: AmneziaConfig, path: str | Path, *, awg_quick: bool = True) -> None:
    """Save configuration to disk.

    When awg_quick=True (default), obfuscation fields are merged into [Interface]
    as expected by awg-quick and amneziawg-go. Otherwise a separate [AmneziaWG]
    section is written for human readability.
    """
    config_path = Path(path)
    lines: list[str] = []

    iface_fields = config.interface.all_fields()
    obf_fields = config.obfuscation.to_interface_fields()

    if awg_quick:
        iface_fields.update(obf_fields)
        _write_section(lines, "Interface", iface_fields)
    else:
        _write_section(lines, "Interface", iface_fields)
        _write_section(lines, "AmneziaWG", obf_fields)

    for peer in config.peers:
        _write_section(lines, "Peer", peer.all_fields())

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
