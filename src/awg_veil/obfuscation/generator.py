"""Generate non-overlapping H1-H4 header ranges."""

from __future__ import annotations

import random
import secrets

from awg_veil.config.models import ObfuscationConfig

H_MIN_BOUND = 5
H_MAX_BOUND = 2_147_483_647
MIN_H_RANGE_SPAN = 10_000_000
NUM_RANGES = 4


def generate_h_ranges(
    *,
    span: int = MIN_H_RANGE_SPAN,
    seed: int | None = None,
) -> dict[str, str]:
    """Generate four non-overlapping H ranges within valid bounds."""
    rng: random.Random | secrets.SystemRandom
    rng = random.Random(seed) if seed is not None else secrets.SystemRandom()

    available_start = H_MIN_BOUND
    available_end = H_MAX_BOUND
    total_needed = NUM_RANGES * span

    if total_needed > available_end - available_start:
        msg = "Cannot fit required H ranges in available space"
        raise ValueError(msg)

    max_start = available_end - total_needed
    base = rng.randint(available_start, max_start)

    ranges: list[tuple[int, int]] = []
    cursor = base
    for _ in range(NUM_RANGES):
        low = cursor
        high = cursor + span - 1
        ranges.append((low, high))
        cursor = high + 1

    return {f"h{i + 1}": f"{low}-{high}" for i, (low, high) in enumerate(ranges)}


def generate_obfuscation(
    *,
    profile_seed: int | None = None,
    s1: int = 16,
    s2: int = 16,
    s3: int = 16,
    s4: int = 32,
    jc: int = 4,
    jmin: int = 128,
    jmax: int = 1024,
) -> ObfuscationConfig:
    """Generate a complete obfuscation config with H ranges."""
    h_ranges = generate_h_ranges(seed=profile_seed)
    return ObfuscationConfig(
        **h_ranges,
        s1=s1,
        s2=s2,
        s3=s3,
        s4=s4,
        jc=jc,
        jmin=jmin,
        jmax=jmax,
    )
