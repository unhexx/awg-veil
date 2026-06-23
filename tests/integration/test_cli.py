"""CLI integration tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from awg_veil.cli.main import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "awg-veil" in result.stdout

def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("init", "gen-config", "validate", "up", "down", "status"):
        assert cmd in result.stdout

def test_init_creates_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AWG_VEIL_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(app, ["init", "awg0"])
    assert result.exit_code == 0
    conf = tmp_path / "awg0.conf"
    assert conf.exists()
    assert "PrivateKey" in conf.read_text()

def test_validate_ok(fixtures_dir: Path) -> None:
    path = fixtures_dir / "amneziawg_section.conf"
    result = runner.invoke(app, ["validate", str(path)])
    assert result.exit_code == 0

def test_validate_invalid(fixtures_dir: Path) -> None:
    path = fixtures_dir / "invalid_overlap.conf"
    result = runner.invoke(app, ["validate", str(path)])
    assert result.exit_code == 1

def test_gen_config_profile(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AWG_VEIL_CONFIG_DIR", str(tmp_path))
    runner.invoke(app, ["init", "awg0"])
    result = runner.invoke(app, ["gen-config", "awg0", "--profile", "censorship_high"])
    assert result.exit_code == 0
    text = (tmp_path / "awg0.conf").read_text()
    assert "H1" in text or "h1" not in text  # merged to interface
    assert "Jc" in text or "jc" in text.lower()

def test_up_down_dry_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AWG_VEIL_CONFIG_DIR", str(tmp_path))
    runner.invoke(app, ["init", "awg0"])
    runner.invoke(app, ["gen-config", "awg0", "--profile", "default"])
    up = runner.invoke(app, ["up", "awg0", "--dry-run", "--skip-validate"])
    assert up.exit_code == 0
    down = runner.invoke(app, ["down", "awg0", "--dry-run"])
    assert down.exit_code == 0

def test_status_dry_run() -> None:
    result = runner.invoke(app, ["status", "--dry-run"])
    assert result.exit_code == 0

def test_validate_missing_file(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", str(tmp_path / "missing.conf")])
    assert result.exit_code == 1

def test_init_existing_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AWG_VEIL_CONFIG_DIR", str(tmp_path))
    runner.invoke(app, ["init", "awg0"])
    result = runner.invoke(app, ["init", "awg0"])
    assert result.exit_code == 1
