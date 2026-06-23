"""WireGuard key generation using cryptography."""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def generate_private_key() -> str:
    """Generate a WireGuard-compatible private key."""
    private_key = X25519PrivateKey.generate()
    raw = private_key.private_bytes_raw()
    return _b64(raw)

def generate_public_key(private_key_b64: str) -> str:
    """Derive public key from a base64 private key."""
    raw = base64.b64decode(private_key_b64)
    private_key = X25519PrivateKey.from_private_bytes(raw)
    public_raw = private_key.public_key().public_bytes_raw()
    return _b64(public_raw)

def generate_keypair() -> tuple[str, str]:
    """Return (private_key, public_key) base64 pair."""
    private = generate_private_key()
    public = generate_public_key(private)
    return private, public

def generate_preshared_key() -> str:
    """Generate a 32-byte preshared key."""
    return _b64(os.urandom(32))
