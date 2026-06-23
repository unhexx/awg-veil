"""awg-veil command-line interface."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from awg_veil import __version__
from awg_veil.config import load_config, save_config, validate_config
from awg_veil.config.models import AmneziaConfig, InterfaceConfig, PeerConfig
from awg_veil.config.validator import Severity
from awg_veil.obfuscation.profiles import PROFILE_NAMES, apply_profile
from awg_veil.secrets.keys import generate_keypair
from awg_veil.tunnel.manager import TunnelManager
from awg_veil.tunnel.mock import MockBackend

app = typer.Typer(
    name="awg-veil",
    help="Vendor-independent CLI for AmneziaWG 2.0",
    no_args_is_help=True,
)
console = Console()
stderr = Console(stderr=True)

EXIT_OK = 0
EXIT_VALIDATION = 1
EXIT_RUNTIME = 2


def _config_dir() -> Path:
    env = os.environ.get("AWG_VEIL_CONFIG_DIR")
    if env:
        return Path(env)
    return Path.home() / ".config" / "awg-veil"


def _resolve_config(name: str, config: Path | None = None) -> Path:
    if config is not None:
        return config
    return _config_dir() / f"{name}.conf"


@app.command("version")
def version_cmd() -> None:
    """Show version."""
    console.print(f"awg-veil {__version__}")


@app.command("init")
def init_cmd(
    name: Annotated[str, typer.Argument(help="Interface/config name (e.g. awg0)")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output config path"),
    ] = None,
    address: Annotated[
        str,
        typer.Option("--address", help="Client address CIDR"),
    ] = "10.8.0.2/32",
) -> None:
    """Create a new config skeleton with generated keys."""
    out_path = output or _resolve_config(name)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        stderr.print(f"[red]Config already exists:[/red] {out_path}")
        raise typer.Exit(EXIT_VALIDATION)

    private, _public = generate_keypair()
    cfg = AmneziaConfig(
        interface=InterfaceConfig(private_key=private, address=[address]),
        peers=[PeerConfig()],
    )
    save_config(cfg, out_path, awg_quick=False)
    console.print(f"[green]Created[/green] {out_path}")
    console.print(
        "Edit [Peer] section (PublicKey, Endpoint, AllowedIPs) before bringing up tunnel."
    )


@app.command("gen-config")
def gen_config_cmd(
    name: Annotated[str, typer.Argument(help="Config name or path")],
    profile: Annotated[
        str,
        typer.Option("--profile", "-p", help="Obfuscation profile"),
    ] = "censorship_high",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output path"),
    ] = None,
    in_place: Annotated[
        bool,
        typer.Option("--in-place", help="Update existing config in place"),
    ] = False,
) -> None:
    """Generate or update obfuscation parameters using a profile."""
    if profile not in PROFILE_NAMES:
        stderr.print(f"[red]Unknown profile:[/red] {profile}. Choose: {', '.join(PROFILE_NAMES)}")
        raise typer.Exit(EXIT_VALIDATION)

    path = output or _resolve_config(name)
    if path.exists():
        cfg = load_config(path)
    else:
        if not in_place and output is None:
            stderr.print(f"[red]Config not found:[/red] {path}. Run 'awg-veil init {name}' first.")
            raise typer.Exit(EXIT_VALIDATION)
        private, _ = generate_keypair()
        cfg = AmneziaConfig(interface=InterfaceConfig(private_key=private, address=["10.8.0.2/32"]))

    cfg = apply_profile(cfg, profile)
    result = validate_config(cfg)
    if not result.ok:
        for issue in result.errors:
            stderr.print(f"[red]ERROR[/red] {issue.field}: {issue.message}")
        raise typer.Exit(EXIT_VALIDATION)

    save_config(cfg, path)
    console.print(f"[green]Applied profile[/green] [bold]{profile}[/bold] → {path}")
    for warn in result.warnings:
        console.print(f"[yellow]WARN[/yellow] {warn.field}: {warn.message}")


@app.command("validate")
def validate_cmd(
    path: Annotated[Path, typer.Argument(help="Config file to validate")],
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Treat warnings as errors"),
    ] = False,
) -> None:
    """Validate an AmneziaWG configuration file."""
    if not path.exists():
        stderr.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(EXIT_VALIDATION)

    try:
        cfg = load_config(path)
    except (ValueError, OSError) as exc:
        stderr.print(f"[red]Parse error:[/red] {exc}")
        raise typer.Exit(EXIT_VALIDATION) from exc

    result = validate_config(cfg)
    table = Table(title=f"Validation: {path}")
    table.add_column("Severity", style="bold")
    table.add_column("Field")
    table.add_column("Message")

    if not result.issues:
        console.print(f"[green]OK[/green] {path} — no issues found")
        raise typer.Exit(EXIT_OK)

    for issue in result.issues:
        style = "red" if issue.severity == Severity.ERROR else "yellow"
        sev = issue.severity.value.upper()
        table.add_row(f"[{style}]{sev}[/{style}]", issue.field, issue.message)

    console.print(table)

    has_errors = not result.ok
    has_warnings = bool(result.warnings)
    if has_errors or (strict and has_warnings):
        raise typer.Exit(EXIT_VALIDATION)
    raise typer.Exit(EXIT_OK)


@app.command("up")
def up_cmd(
    name: Annotated[str, typer.Argument(help="Interface name (e.g. awg0)")],
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="Config file path"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Use mock backend (no root required)"),
    ] = False,
    skip_validate: Annotated[
        bool,
        typer.Option("--skip-validate", help="Skip pre-flight validation"),
    ] = False,
) -> None:
    """Bring up an AmneziaWG tunnel."""
    config_path = _resolve_config(name, config)

    if not config_path.exists():
        stderr.print(f"[red]Config not found:[/red] {config_path}")
        raise typer.Exit(EXIT_VALIDATION)

    if not skip_validate:
        cfg = load_config(config_path)
        result = validate_config(cfg)
        if not result.ok:
            for issue in result.errors:
                stderr.print(f"[red]ERROR[/red] {issue.field}: {issue.message}")
            stderr.print("Fix errors or pass --skip-validate to override.")
            raise typer.Exit(EXIT_VALIDATION)

    backend = MockBackend() if dry_run else None
    mgr = TunnelManager(name, backend=backend)
    try:
        mgr.up(str(config_path))
    except (RuntimeError, FileNotFoundError) as exc:
        stderr.print(f"[red]Failed to bring up tunnel:[/red] {exc}")
        raise typer.Exit(EXIT_RUNTIME) from exc

    mode = " (dry-run)" if dry_run else ""
    console.print(f"[green]Tunnel up[/green]{mode}: {name} ← {config_path}")


@app.command("down")
def down_cmd(
    name: Annotated[str, typer.Argument(help="Interface name")],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Use mock backend"),
    ] = False,
) -> None:
    """Bring down an AmneziaWG tunnel."""
    backend = MockBackend() if dry_run else None
    mgr = TunnelManager(name, backend=backend)
    try:
        mgr.down()
    except RuntimeError as exc:
        stderr.print(f"[red]Failed to bring down tunnel:[/red] {exc}")
        raise typer.Exit(EXIT_RUNTIME) from exc

    mode = " (dry-run)" if dry_run else ""
    console.print(f"[green]Tunnel down[/green]{mode}: {name}")


@app.command("status")
def status_cmd(
    name: Annotated[
        str | None,
        typer.Argument(help="Interface name (optional)"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Use mock backend"),
    ] = False,
) -> None:
    """Show tunnel status."""
    backend = MockBackend() if dry_run else None
    iface = name or "all"
    mgr = TunnelManager(iface if name else "awg0", backend=backend)
    try:
        st = mgr.status() if name else (backend or mgr._backend).status(None)  # noqa: SLF001
    except RuntimeError as exc:
        stderr.print(f"[red]Status query failed:[/red] {exc}")
        raise typer.Exit(EXIT_RUNTIME) from exc

    state = "[green]up[/green]" if st.is_up else "[red]down[/red]"
    console.print(f"Interface [bold]{st.interface}[/bold]: {state}")
    if st.raw_output.strip():
        console.print(st.raw_output)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
