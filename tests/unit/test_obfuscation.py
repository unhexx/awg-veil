"""Tests for obfuscation generation."""

from __future__ import annotations

from awg_veil.config.models import AmneziaConfig, InterfaceConfig
from awg_veil.config.validator import validate_config
from awg_veil.obfuscation.cps import CPSBuilder
from awg_veil.obfuscation.generator import generate_h_ranges, generate_obfuscation
from awg_veil.obfuscation.profiles import PROFILE_NAMES, apply_profile, build_profile


def test_generate_h_ranges_non_overlapping() -> None:
    ranges = generate_h_ranges(seed=42)
    assert len(ranges) == 4
    parsed = []
    for key in ("h1", "h2", "h3", "h4"):
        low, high = map(int, ranges[key].split("-"))
        parsed.append((low, high))
    for i, (lo_a, hi_a) in enumerate(parsed):
        for lo_b, hi_b in parsed[i + 1:]:
            assert hi_a < lo_b or hi_b < lo_a

def test_cps_builder() -> None:
    cps = CPSBuilder().add_bytes("abcd").add_timestamp().add_random(16).build()
    assert "<b 0xabcd>" in cps
    assert "<t>" in cps
    assert "<r 16>" in cps

def test_all_profiles_build() -> None:
    for name in PROFILE_NAMES:
        obf = build_profile(name)
        cfg = AmneziaConfig(
            interface=InterfaceConfig(private_key="abc="),
            obfuscation=obf,
        )
        result = validate_config(cfg)
        assert result.ok, f"Profile {name} failed: {result.errors}"

def test_apply_profile() -> None:
    cfg = AmneziaConfig(interface=InterfaceConfig(private_key="abc="))
    updated = apply_profile(cfg, "censorship_high")
    assert updated.obfuscation.jc == 6
    assert updated.obfuscation.i1 is not None

def test_generate_obfuscation_deterministic() -> None:
    a = generate_obfuscation(profile_seed=99)
    b = generate_obfuscation(profile_seed=99)
    assert a.h1 == b.h1
