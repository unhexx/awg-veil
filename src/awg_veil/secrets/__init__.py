"""Key generation for WireGuard / AmneziaWG."""

from awg_veil.secrets.keys import generate_keypair, generate_preshared_key

__all__ = ["generate_keypair", "generate_preshared_key"]