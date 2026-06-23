"""Obfuscation profile generation for AmneziaWG 2.0."""

from awg_veil.obfuscation.cps import CPSBuilder
from awg_veil.obfuscation.generator import generate_h_ranges
from awg_veil.obfuscation.profiles import PROFILE_NAMES, apply_profile

__all__ = ["CPSBuilder", "PROFILE_NAMES", "apply_profile", "generate_h_ranges"]