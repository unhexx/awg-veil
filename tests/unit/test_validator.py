"""Tests for config validator."""

from __future__ import annotations

from pathlib import Path

from awg_veil.config.models import AmneziaConfig, InterfaceConfig, ObfuscationConfig
from awg_veil.config.parser import load_config
from awg_veil.config.validator import Severity, parse_range, validate_config


def test_parse_range_single() -> None:
    assert parse_range("12345") == (12345, 12345)

def test_parse_range_pair() -> None:
    assert parse_range("100-200") == (100, 200)

def test_valid_config_passes(fixtures_dir: Path) -> None:
    cfg = load_config(fixtures_dir / "amneziawg_section.conf")
    result = validate_config(cfg)
    assert result.ok

def test_overlapping_h_ranges_fail(fixtures_dir: Path) -> None:
    cfg = load_config(fixtures_dir / "invalid_overlap.conf")
    result = validate_config(cfg)
    assert not result.ok
    assert any("overlap" in i.message.lower() for i in result.errors)

def test_h_range_includes_wg_type_id() -> None:
    cfg = AmneziaConfig(
        interface=InterfaceConfig(private_key="abc="),
        obfuscation=ObfuscationConfig(h1="1-100"),
    )
    result = validate_config(cfg)
    assert not result.ok
    assert any("type-id" in i.message for i in result.errors)

def test_jmin_gte_jmax() -> None:
    cfg = AmneziaConfig(
        interface=InterfaceConfig(private_key="abc="),
        obfuscation=ObfuscationConfig(jmin=512, jmax=128),
    )
    result = validate_config(cfg)
    assert not result.ok

def test_invalid_cps_syntax() -> None:
    cfg = AmneziaConfig(
        interface=InterfaceConfig(private_key="abc="),
        obfuscation=ObfuscationConfig(i1="not-valid-cps"),
    )
    result = validate_config(cfg)
    assert not result.ok
    assert any(i.field == "i1" for i in result.errors)

def test_valid_cps_syntax() -> None:
    cfg = AmneziaConfig(
        interface=InterfaceConfig(private_key="abc="),
        obfuscation=ObfuscationConfig(i1="<b 0xabcd><t><r 32>"),
    )
    result = validate_config(cfg)
    assert not any(i.field == "i1" and i.severity == Severity.ERROR for i in result.issues)

def test_weak_profile_warning() -> None:
    cfg = AmneziaConfig(interface=InterfaceConfig(private_key="abc="))
    result = validate_config(cfg)
    assert any(i.severity == Severity.WARNING for i in result.issues)

def test_missing_private_key() -> None:
    cfg = AmneziaConfig(interface=InterfaceConfig())
    result = validate_config(cfg)
    assert not result.ok
