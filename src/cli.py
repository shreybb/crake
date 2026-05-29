"""Crake Typer CLI — same dispatch layer as the Streamlit app."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from src.agent.command_runner import execute_command
from src.agent.tool_dispatch import dispatch
from src.session.construct import ConstructSession

app = typer.Typer(
    name="crake",
    help="Deterministic plasmid design workbench (CLI)",
    no_args_is_help=True,
)
session_app = typer.Typer(help="Run commands against a saved session JSON file")
app.add_typer(session_app, name="session")


def _session_dict(path: Path | None) -> dict:
    if path is None:
        return {}
    data = json.loads(path.read_text())
    if "last_sequence" in data or "sequence" not in data:
        return data
    return ConstructSession.from_state_dict(data).to_state_dict()


@session_app.command("export")
def session_export(
    session_file: Path = typer.Argument(..., help="Saved session JSON"),
    name: str = typer.Option("pConstruct", "--name", "-n"),
    output_dir: Path = typer.Option(Path("./crake_output"), "--output-dir", "-o"),
    allow_sequence_only: bool = typer.Option(
        False,
        "--allow-sequence-only",
        help="Export without simulated assembly",
    ),
) -> None:
    """Export from a session file."""
    state = _session_dict(session_file)
    dispatch(
        "export_files",
        {
            "name": name,
            "output_dir": str(output_dir),
            "allow_sequence_only": allow_sequence_only,
        },
        state,
    )
    typer.echo(json.dumps(state.get("export_paths", {}), indent=2))


@session_app.command("run")
def session_run(
    session_file: Path = typer.Argument(...),
    command: str = typer.Argument(..., help='Slash command, e.g. "/optimize yeast"'),
) -> None:
    """Run one slash command against a session file and write back."""
    state = _session_dict(session_file)
    from src.agent.commands import parse_input, validate_command

    cmd_name, args = parse_input(command)
    if not cmd_name:
        raise typer.BadParameter("Command must start with /")
    validate_command(cmd_name)
    execute_command(cmd_name, args, state)
    session_file.write_text(json.dumps(state, indent=2, default=str))
    typer.echo(f"Updated {session_file}")


@app.command("cmd")
def run_cmd(
    command: str = typer.Argument(..., help='Slash command, e.g. "/validate"'),
    session_out: Optional[Path] = typer.Option(
        None, "--session-out", help="Write session state to JSON after run"
    ),
) -> None:
    """Execute a slash command (ephemeral session unless --session-out)."""
    from src.agent.commands import parse_input, validate_command

    state: dict = {}
    cmd_name, args = parse_input(command)
    if not cmd_name:
        raise typer.BadParameter("Command must start with /")
    validate_command(cmd_name)
    tool_name, message, result = execute_command(cmd_name, args, state)
    typer.echo(message)
    if result.get("error"):
        raise typer.Exit(1)
    if session_out:
        session_out.write_text(json.dumps(state, indent=2, default=str))
        typer.echo(f"Session written to {session_out}", err=True)


@app.command("version")
def version() -> None:
    """Print package version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("crake"))


if __name__ == "__main__":
    app()
