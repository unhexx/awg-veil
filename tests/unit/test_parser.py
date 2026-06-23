"""Tests for config parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from awg_veil.config.models import AmneziaConfig, InterfaceConfig, ObfuscationConfig, PeerConfig
from awg_veil.config.parser import load_config, save_config


def test_load_native_format(fixtures_dir: Path) -> None:
    cfg = load_config(fixtures_dir / "native.conf")
    assert cfg.interface.private_key is not None
    assert cfg.interface.address == ["10.8.0.2/32"]
    assert cfg.obfuscation.jc == 3
    assert cfg.obfuscation.h1 == "191091632-238083235"
    assert cfg.obfuscation.i1 is not None
    assert len(cfg.peers) == 1
    assert cfg.peers[0].endpoint == "1.2.3.4:51820"

def test_load_amneziawg_section(fixtures_dir: Path) -> None:
    cfg = load_config(fixtures_dir / "amneziawg_section.conf")
    assert cfg.obfuscation.h1 == "100000000-200000000"
    assert cfg.obfuscation.s4 == 32
    assert cfg.interface.private_key is not None
    assert "obfuscation" not in cfg.interface.extra

def test_save_merge_to_interface(tmp_path: Path) -> None:
    cfg = AmneziaConfig(
        interface=InterfaceConfig(private_key="abc=", address=["10.0.0.1/32"]),
        peers=[PeerConfig(public_key="def=", allowed_ips=["0.0.0.0/0"])],
        obfuscation=ObfuscationConfig(h1="100-200", s1=16, jc=4, jmin=128, jmax=512),
    )
    out = tmp_path / "out.conf"
    save_config(cfg, out, awg_quick=True)
    text = out.read_text()
    assert "[AmneziaWG]" not in text
    assert "H1 = 100-200" in text
    assert "S1 = 16" in text
    assert "[Interface]" in text
    assert "[Peer]" in text

def test_save_separate_section(tmp_path: Path) -> None:
    cfg = AmneziaConfig(
        interface=InterfaceConfig(private_key="abc="),
        obfuscation=ObfuscationConfig(h1="100-200"),
    )
    out = tmp_path / "out.conf"
    save_config(cfg, out, awg_quick=False)
    text = out.read_text()
    assert "[AmneziaWG]" in text
    assert "H1 = 100-200" in text

def test_roundtrip(tmp_path: Path, fixtures_dir: Path) -> None:
    original = load_config(fixtures_dir / "amneziawg_section.conf")
    out = tmp_path / "roundtrip.conf"
    save_config(original, out, awg_quick=True)
    restored = load_config(out)
    assert restored.obfuscation.h1 == original.obfuscation.h1
    assert restored.obfuscation.jmax == original.obfuscation.jmax
    assert restored.peers[0].endpoint == original.peers[0].endpoint

def test_missing_interface_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.conf"
    bad.write_text("[Peer]\nPublicKey = abc=\n")
    with pytest.raises(ValueError, match="Missing \\[Interface\\]"):
        load_config(bad)
