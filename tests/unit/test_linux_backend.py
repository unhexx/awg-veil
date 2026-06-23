"""Tests for Linux tunnel backend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from awg_veil.tunnel.linux import LinuxBackend, _redact_output


def test_redact_sensitive_output() -> None:
    text = "PrivateKey = abc123\nPresharedKey = def456\n"
    redacted = _redact_output(text)
    assert "abc123" not in redacted
    assert "<redacted>" in redacted

def test_up_missing_awg_quick() -> None:
    backend = LinuxBackend(awg_quick_bin=None, awg_bin="/usr/bin/awg")
    with pytest.raises(RuntimeError, match="awg-quick not found"):
        backend.up("awg0", "/tmp/test.conf")

def test_up_success() -> None:
    backend = LinuxBackend(awg_quick_bin="/usr/bin/awg-quick", awg_bin="/usr/bin/awg")
    with patch("awg_veil.tunnel.linux.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        with patch("awg_veil.tunnel.linux.Path.exists", return_value=True):
            backend.up("awg0", "/tmp/test.conf")
        mock_run.assert_called_once()

def test_up_failure_redacts_keys() -> None:
    backend = LinuxBackend(awg_quick_bin="/usr/bin/awg-quick", awg_bin="/usr/bin/awg")
    with patch("awg_veil.tunnel.linux.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="PrivateKey = secretkey\nfailed",
        )
        with (
            patch("awg_veil.tunnel.linux.Path.exists", return_value=True),
            pytest.raises(RuntimeError, match="<redacted>"),
        ):
            backend.up("awg0", "/tmp/test.conf")

def test_status_parses_output() -> None:
    backend = LinuxBackend(awg_quick_bin="/usr/bin/awg-quick", awg_bin="/usr/bin/awg")
    with patch("awg_veil.tunnel.linux.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="interface: awg0\n  listening port: 51820\n",
        )
        st = backend.status("awg0")
        assert st.is_up
        assert "awg0" in st.raw_output
