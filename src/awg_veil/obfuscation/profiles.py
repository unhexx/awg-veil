"""Predefined obfuscation profiles."""

from __future__ import annotations

from awg_veil.config.models import AmneziaConfig, ObfuscationConfig
from awg_veil.obfuscation.cps import CPSBuilder
from awg_veil.obfuscation.generator import generate_obfuscation

PROFILE_NAMES = ("default", "censorship_medium", "censorship_high")

_PROFILE_SETTINGS: dict[str, dict[str, int]] = {
    "default": {
        "s1": 8, "s2": 8, "s3": 8, "s4": 16,
        "jc": 2, "jmin": 200, "jmax": 512,
    },
    "censorship_medium": {
        "s1": 16, "s2": 16, "s3": 16, "s4": 24,
        "jc": 4, "jmin": 200, "jmax": 768,
    },
    "censorship_high": {
        "s1": 24, "s2": 20, "s3": 32, "s4": 32,
        "jc": 6, "jmin": 200, "jmax": 1024,
    },
}


def _profile_seed(name: str) -> int:
    return sum(ord(c) for c in name) * 1_000_003


def build_profile(name: str) -> ObfuscationConfig:
    """Build obfuscation config for a named profile."""
    if name not in PROFILE_NAMES:
        msg = f"Unknown profile {name!r}; choose from {PROFILE_NAMES}"
        raise ValueError(msg)

    settings = _PROFILE_SETTINGS[name]
    obf = generate_obfuscation(profile_seed=_profile_seed(name), **settings)

    if name in ("censorship_medium", "censorship_high"):
        obf = obf.model_copy(
            update={
                "i1": CPSBuilder.quic_initial_template(),
                "i2": CPSBuilder().add_random(32).add_timestamp().build(),
                "i3": (
                    CPSBuilder().add_random_chars(16).build()
                    if name == "censorship_high"
                    else None
                ),
            }
        )
    return obf


def apply_profile(config: AmneziaConfig, profile: str) -> AmneziaConfig:
    """Apply an obfuscation profile to an existing config."""
    obf = build_profile(profile)
    return config.model_copy(update={"obfuscation": obf})
