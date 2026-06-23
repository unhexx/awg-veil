"""Validation rules for AmneziaWG 2.0 configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from awg_veil.config.models import AmneziaConfig, ObfuscationConfig

WG_TYPE_IDS = {1, 2, 3, 4}
WG_RAW_SIZES = {148, 92, 64, 32}
H_MIN_BOUND = 5
H_MAX_BOUND = 2_147_483_647
MIN_H_RANGE_SPAN = 10_000

CPS_TAG_PATTERN = re.compile(
    r"<(b\s+[0-9a-fA-Fx]+|t|d|r\s+\d+|rc\s+\d+|rd\s+\d+)>",
)


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    field: str
    message: str
    severity: Severity = Severity.ERROR


@dataclass
class ValidationResult:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]


def parse_range(value: str) -> tuple[int, int]:
    """Parse H range like '100000-200000' or single value '12345'."""
    value = value.strip()
    if "-" in value:
        parts = value.split("-", 1)
        return int(parts[0].strip()), int(parts[1].strip())
    num = int(value)
    return num, num


def validate_config(config: AmneziaConfig) -> ValidationResult:
    """Validate a complete AmneziaWG configuration."""
    result = ValidationResult()
    _validate_interface(config, result)
    _validate_peers(config, result)
    if not config.obfuscation.is_empty():
        _validate_obfuscation(config.obfuscation, result)
    return result


def _validate_interface(config: AmneziaConfig, result: ValidationResult) -> None:
    iface = config.interface
    if not iface.private_key:
        result.issues.append(ValidationIssue("interface.private_key", "PrivateKey is required"))
    if not iface.address and not config.peers:
        result.issues.append(
            ValidationIssue(
                "interface.address",
                "Address is required for client configs",
                Severity.WARNING,
            )
        )


def _validate_peers(config: AmneziaConfig, result: ValidationResult) -> None:
    if not config.peers:
        result.issues.append(
            ValidationIssue("peers", "At least one [Peer] section is recommended", Severity.WARNING)
        )
    for idx, peer in enumerate(config.peers):
        prefix = f"peers[{idx}]"
        if not peer.public_key:
            result.issues.append(ValidationIssue(f"{prefix}.public_key", "PublicKey is required"))
        if not peer.allowed_ips:
            result.issues.append(
                ValidationIssue(
                    f"{prefix}.allowed_ips",
                    "AllowedIPs is recommended",
                    Severity.WARNING,
                )
            )


def _validate_obfuscation(obf: ObfuscationConfig, result: ValidationResult) -> None:
    _validate_h_ranges(obf, result)
    _validate_s_params(obf, result)
    _validate_j_params(obf, result)
    _validate_i_params(obf, result)
    _validate_weak_profile(obf, result)


def _validate_h_ranges(obf: ObfuscationConfig, result: ValidationResult) -> None:
    ranges: list[tuple[str, int, int]] = []
    for name in ("h1", "h2", "h3", "h4"):
        value = getattr(obf, name)
        if value is None:
            continue
        try:
            low, high = parse_range(value)
        except ValueError:
            result.issues.append(ValidationIssue(name, f"Invalid H range format: {value}"))
            continue
        if low > high:
            result.issues.append(ValidationIssue(name, f"H range min ({low}) > max ({high})"))
        if low < H_MIN_BOUND or high > H_MAX_BOUND:
            result.issues.append(
                ValidationIssue(name, f"H range must be within {H_MIN_BOUND}..{H_MAX_BOUND}")
            )
        if high - low < MIN_H_RANGE_SPAN and low != high:
            result.issues.append(
                ValidationIssue(
                    name,
                    f"H range span ({high - low}) below minimum ({MIN_H_RANGE_SPAN})",
                    Severity.WARNING,
                )
            )
        for wg_id in WG_TYPE_IDS:
            if low <= wg_id <= high:
                result.issues.append(
                    ValidationIssue(name, f"H range must not include WireGuard type-id {wg_id}")
                )
        ranges.append((name, low, high))

    for i, (name_a, lo_a, hi_a) in enumerate(ranges):
        for name_b, lo_b, hi_b in ranges[i + 1:]:
            if lo_a <= hi_b and lo_b <= hi_a:
                result.issues.append(
                    ValidationIssue(
                        name_a,
                        f"H range {name_a} ({lo_a}-{hi_a}) overlaps with {name_b} ({lo_b}-{hi_b})",
                    )
                )


def _validate_s_params(obf: ObfuscationConfig, result: ValidationResult) -> None:
    limits = {"s1": 64, "s2": 64, "s3": 64, "s4": 32}
    bases = {"s1": 148, "s2": 92, "s3": 64, "s4": 32}
    padded: dict[str, int] = {}

    for name, limit in limits.items():
        value = getattr(obf, name)
        if value is None:
            continue
        if value < 0 or value > limit:
            result.issues.append(ValidationIssue(name, f"{name.upper()} must be 0..{limit}"))
        padded[name] = bases[name] + value

    sizes = list(padded.values())
    for i, size_a in enumerate(sizes):
        for size_b in sizes[i + 1:]:
            if size_a == size_b:
                result.issues.append(
                    ValidationIssue(
                        "s1-s4",
                        f"Padded packet sizes must be distinct; duplicate {size_a}",
                    )
                )

    s1, s2 = obf.s1, obf.s2
    if s1 is not None and s2 is not None and s1 + 56 == s2:
        result.issues.append(
            ValidationIssue("s1/s2", "S1+56 must not equal S2 (Init/Response size collision)")
        )


def _validate_j_params(obf: ObfuscationConfig, result: ValidationResult) -> None:
    jc, jmin, jmax = obf.jc, obf.jmin, obf.jmax
    if jc is not None and (jc < 0 or jc > 10):
        result.issues.append(ValidationIssue("jc", "Jc must be 0..10"))
    if jmin is not None and (jmin < 64 or jmin > 1024):
        result.issues.append(ValidationIssue("jmin", "Jmin must be 64..1024"))
    if jmax is not None and (jmax < 64 or jmax > 1024):
        result.issues.append(ValidationIssue("jmax", "Jmax must be 64..1024"))
    if jmin is not None and jmax is not None and jmin >= jmax:
        result.issues.append(ValidationIssue("jmin/jmax", "Jmin must be less than Jmax"))

    if jmin is not None and jmax is not None:
        forbidden = set(WG_RAW_SIZES)
        if obf.s1 is not None:
            forbidden.add(148 + obf.s1)
        if obf.s2 is not None:
            forbidden.add(92 + obf.s2)
        if obf.s3 is not None:
            forbidden.add(64 + obf.s3)
        if obf.s4 is not None:
            forbidden.add(32 + obf.s4)
        overlap = [s for s in forbidden if jmin <= s <= jmax]
        if overlap:
            result.issues.append(
                ValidationIssue(
                    "jmin/jmax",
                    f"Junk range [{jmin}..{jmax}] must not contain WG/padded sizes: {overlap}",
                )
            )


def _validate_i_params(obf: ObfuscationConfig, result: ValidationResult) -> None:
    for name in ("i1", "i2", "i3", "i4", "i5"):
        value = getattr(obf, name)
        if value is None or not value.strip():
            continue
        _validate_cps(name, value, result)


def _validate_cps(field: str, value: str, result: ValidationResult) -> None:
    stripped = value.strip()
    if not stripped:
        return
    # Must consist entirely of valid CPS tags
    pos = 0
    matched_any = False
    for match in CPS_TAG_PATTERN.finditer(stripped):
        matched_any = True
        if match.start() != pos:
            result.issues.append(
                ValidationIssue(field, f"Invalid CPS syntax near position {pos}: {value!r}")
            )
            return
        pos = match.end()
    if pos != len(stripped):
        result.issues.append(ValidationIssue(field, f"Invalid CPS syntax: {value!r}"))
    if not matched_any:
        result.issues.append(
            ValidationIssue(field, f"CPS must contain at least one tag: {value!r}")
        )


def _validate_weak_profile(obf: ObfuscationConfig, result: ValidationResult) -> None:
    """Warn when obfuscation is effectively disabled."""
    has_h = any(getattr(obf, f"h{i}") for i in range(1, 5))
    has_s = any(
        getattr(obf, f"s{i}") is not None and getattr(obf, f"s{i}") > 0
        for i in range(1, 5)
    )
    has_j = obf.jc is not None and obf.jc > 0
    has_i = any(getattr(obf, f"i{i}") for i in range(1, 6))

    if not (has_h or has_s or has_j or has_i):
        result.issues.append(
            ValidationIssue(
                "obfuscation",
                "No obfuscation parameters set; traffic will resemble standard WireGuard",
                Severity.WARNING,
            )
        )
