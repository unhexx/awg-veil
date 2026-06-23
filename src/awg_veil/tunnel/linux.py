"""Linux tunnel backend using awg-quick and awg."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from awg_veil.tunnel.base import TunnelBackend, TunnelStatus

_SENSITIVE_PATTERN = re.compile(
    r"(PrivateKey|PresharedKey)\s*=\s*\S+",
    re.IGNORECASE,
)


def _redact_output(text: str) -> str:
    """Remove sensitive key material from command output."""
    return _SENSITIVE_PATTERN.sub(r"\1 = <redacted>", text)


class LinuxBackend(TunnelBackend):
    """Manage tunnels via awg-quick and awg on Linux."""

    def __init__(
        self,
        awg_quick_bin: str | None = None,
        awg_bin: str | None = None,
    ) -> None:
        self.awg_quick = awg_quick_bin or shutil.which("awg-quick")
        self.awg = awg_bin or shutil.which("awg")

    def _require_awg_quick(self) -> str:
        if not self.awg_quick:
            msg = "awg-quick not found in PATH; install amneziawg-tools"
            raise RuntimeError(msg)
        return self.awg_quick

    def _require_awg(self) -> str:
        if not self.awg:
            msg = "awg not found in PATH; install amneziawg-tools"
            raise RuntimeError(msg)
        return self.awg

    def up(self, interface: str, config_path: str) -> None:
        awg_quick = self._require_awg_quick()
        path = Path(config_path)
        if not path.exists():
            msg = f"Config not found: {config_path}"
            raise FileNotFoundError(msg)
        result = subprocess.run(
            [awg_quick, "up", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = _redact_output(result.stderr)
            msg = f"awg-quick up failed (exit {result.returncode}): {stderr}"
            raise RuntimeError(msg)

    def down(self, interface: str) -> None:
        awg_quick = self._require_awg_quick()
        result = subprocess.run(
            [awg_quick, "down", interface],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = _redact_output(result.stderr)
            msg = f"awg-quick down failed (exit {result.returncode}): {stderr}"
            raise RuntimeError(msg)

    def status(self, interface: str | None = None) -> TunnelStatus:
        awg = self._require_awg()
        cmd = [awg, "show"]
        if interface:
            cmd.append(interface)
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        output = _redact_output(result.stdout)
        is_up = "interface:" in output.lower() or bool(output.strip())
        return TunnelStatus(
            interface=interface or "all",
            is_up=is_up and result.returncode == 0,
            raw_output=output,
        )
