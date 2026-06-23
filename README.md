# awg-veil

VeilAWG — удобный вендоронезависимый клиент и Python-библиотека для AmneziaWG 2.0. Продвинутая обфускация, Docker-first и готовность к AI-агентам. MIT.

VeilAWG — vendor-independent CLI client and Python library for AmneziaWG 2.0 with advanced traffic obfuscation. Docker-first and agentic-ready. MIT licensed.

[![CI](https://github.com/unhexx/awg-veil/actions/workflows/ci.yml/badge.svg)](https://github.com/unhexx/awg-veil/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-GPLv3-green)

## Features

- Parse and validate AmneziaWG 2.0 configs (H1–H4, S1–S4, Jc/Jmin/Jmax, I1–I5 CPS)
- Generate obfuscation profiles: `default`, `censorship_medium`, `censorship_high`
- Manage tunnels via `awg-quick` (Linux)
- No telemetry, no vendor lock-in — works with configs from AmneziaVPN, GL.iNet, amnezigo

## Requirements

| Component | Source |
|-----------|--------|
| Python 3.11+ | system |
| [amneziawg-tools](https://github.com/amnezia-vpn/amneziawg-tools) | AUR / build from source |
| [amneziawg-go](https://github.com/amnezia-vpn/amneziawg-go) | AUR / build from source |

On Arch Linux:

```bash
# AUR packages (names may vary)
yay -S amneziawg-tools amneziawg-go
```

## Quick start

```bash
# Install
git clone https://github.com/unhexx/awg-veil.git
cd awg-veil
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Create config skeleton
awg-veil init awg0

# Apply obfuscation profile
awg-veil gen-config awg0 --profile censorship_high

# Edit ~/.config/awg-veil/awg0.conf — set Peer PublicKey, Endpoint, AllowedIPs

# Validate
awg-veil validate ~/.config/awg-veil/awg0.conf

# Bring tunnel up (requires root)
sudo awg-veil up awg0

# Status & teardown
awg-veil status awg0
sudo awg-veil down awg0
```

### Dry-run (no root, no awg-quick)

```bash
awg-veil up awg0 --dry-run --skip-validate
awg-veil down awg0 --dry-run
```

## CLI commands

| Command | Description |
|---------|-------------|
| `init <name>` | Create config skeleton with generated keys |
| `gen-config <name> --profile <p>` | Apply obfuscation profile |
| `validate <path>` | Validate config (use `--strict` to fail on warnings) |
| `up <iface>` | Start tunnel via `awg-quick` |
| `down <iface>` | Stop tunnel |
| `status [iface]` | Show tunnel status |

Config directory: `~/.config/awg-veil/` (override with `AWG_VEIL_CONFIG_DIR`).

## Python API

```python
from awg_veil import AmneziaConfig
from awg_veil.config import validate_config
from awg_veil.obfuscation import apply_profile
from awg_veil.tunnel import TunnelManager

cfg = AmneziaConfig.from_file("awg0.conf")
cfg = apply_profile(cfg, "censorship_high")
result = validate_config(cfg)
assert result.ok

cfg.to_file("/etc/amneziawg/awg0.conf")  # merges [AmneziaWG] → [Interface]

mgr = TunnelManager("awg0")
mgr.up("/etc/amneziawg/awg0.conf")
print(mgr.status().raw_output)
mgr.down()
```

## Obfuscation profiles

| Profile | Jc | S1–S4 | CPS (I1–I3) |
|---------|-----|-------|-------------|
| `default` | 2 | light padding | — |
| `censorship_medium` | 4 | medium | I1, I2 |
| `censorship_high` | 6 | strong | I1, I2, I3 |

See [docs/configuration.md](docs/configuration.md) for full parameter reference.

## Development

```bash
pip install -e ".[dev]"
make check    # lint + typecheck + tests (85% coverage)
```

## Architecture

```
CLI (Typer) → awg_veil library → awg-quick / amneziawg-go
                 ├─── config     (parse, validate, merge)
                 ├─── obfuscation (profiles, CPS builder)
                 ├─── tunnel     (Linux subprocess / mock)
                 └─── secrets    (WireGuard key generation)
```

## License

GPLv3 — compatible with [amneziawg-tools](https://github.com/amnezia-vpn/amneziawg-tools) and [amneziawg-go](https://github.com/amnezia-vpn/amneziawg-go).

## Links

- [AmneziaWG documentation](https://docs.amnezia.org/documentation/amnezia-wg/)
- [Design document (RU)](%D0%9F%D1%80%D0%BE%D0%B5%D0%BA%D1%82%20%D0%BA%D0%BE%D0%BD%D1%81%D0%BE%D0%BB%D1%8C%D0%BD%D0%BE%D0%B3%D0%BE%20%D0%BA%D0%BB%D0%B8%D0%B5%D0%BD%D1%82%D0%B0%20%D0%B8%20%D0%B1%D0%B8%D0%B1%D0%BB%D0%B8%D0%BE%D1%82%D0%B5%D0%BA%D0%B8%20Python%20%D0%B4%D0%BB%D1%8F%20AmneziaWG%202.0.md)
