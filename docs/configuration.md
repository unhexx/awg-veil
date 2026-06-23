# AmneziaWG 2.0 Configuration Reference

## Format

awg-veil supports two on-disk layouts:

1. **Native** — obfuscation fields inside `[Interface]` (used by `awg-quick`)
2. **Logical** — separate `[AmneziaWG]` section (easier to edit; merged on export)

When saving for tunnel use, awg-veil merges `[AmneziaWG]` into `[Interface]` automatically.

## Parameters

### H1–H4 (dynamic headers)

| Rule | Description |
|------|-------------|
| Format | `min-max` or single integer |
| Bounds | 5 .. 2_147_483_647 |
| Isolation | Must not include WireGuard type-ids 1–4 |
| Overlap | Ranges must not overlap |

### S1–S4 (padding)

| Param | Range | Effective size |
|-------|-------|----------------|
| S1 | 0–64 | Init: 148 + S1 |
| S2 | 0–64 | Response: 92 + S2 |
| S3 | 0–64 | Cookie: 64 + S3 |
| S4 | 0–32 | Transport: 32 + S4 |

All padded sizes must be pairwise distinct.

### Jc, Jmin, Jmax (junk train)

| Param | Range |
|-------|-------|
| Jc | 0–10 |
| Jmin, Jmax | 64–1024, Jmin < Jmax |

Junk length range must not contain raw or padded WireGuard packet sizes.

### I1–I5 (CPS packets)

Client-only. Syntax:

```text
<b 0xhex>   static bytes
<t>         Unix timestamp
<r N>       N random bytes
<rc N>      N random ASCII letters
<rd N>      N random digits
```

## Obfuscation profiles

| Profile | Use case |
|---------|----------|
| `default` | Light obfuscation |
| `censorship_medium` | Moderate DPI environments |
| `censorship_high` | Aggressive censorship (full H/S/J/I) |

Generate with:

```bash
awg-veil gen-config awg0 --profile censorship_high
```

## Vendor compatibility

Configs from AmneziaVPN, GL.iNet routers, and [amnezigo](https://github.com/Arsolitt/amnezigo) are supported when they use standard AmneziaWG 2.0 fields.
