"""Tests for key generation."""

from __future__ import annotations

import base64

from awg_veil.secrets.keys import generate_keypair, generate_preshared_key, generate_public_key


def test_generate_keypair() -> None:
    private, public = generate_keypair()
    assert len(base64.b64decode(private)) == 32
    assert len(base64.b64decode(public)) == 32
    assert generate_public_key(private) == public

def test_generate_preshared_key() -> None:
    psk = generate_preshared_key()
    assert len(base64.b64decode(psk)) == 32
