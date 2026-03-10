"""
Dev Activity Logger — CLI entry point.
Usage: python -m cli.main <command>
"""

from typing import Optional
import typer

from cli.commands import (
    cmd_init,
    cmd_today,
    cmd_week,
    cmd_report,
    cmd_install_hook,
)

app = typer.Typer(
    name="devlog",
    help="Dev Activity Logger — automatically track and analyse your development activity.",
    add_completion=False,
    invoke_without_command=True,   # allow callback to fire with no subcommand
    no_args_is_help=False,         # we handle the no-args case ourselves
)

__version__ = "1.0.0"

_ASCII_BANNER = """\
[bold cyan]
  ██████╗ ███████╗██╗   ██╗    ██╗      ██████╗  ██████╗ 
  ██╔══██╗██╔════╝██║   ██║    ██║     ██╔═══██╗██╔════╝ 
  ██║  ██║█████╗  ██║   ██║    ██║     ██║   ██║██║  ███╗
  ██║  ██║██╔══╝  ╚██╗ ██╔╝    ██║     ██║   ██║██║   ██║
  ██████╔╝███████╗ ╚████╔╝     ███████╗╚██████╔╝╚██████╔╝
  ╚═════╝ ╚══════╝  ╚═══╝      ╚══════╝ ╚═════╝  ╚═════╝ 
[/bold cyan]"""

_JARGON = "[italic dim]Your code speaks. devlog listens.[/italic dim]"


def _print_welcome():
    from rich.console import Console
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text

    console = Console()
    console.print(_ASCII_BANNER)
    console.print(f"  {_JARGON}\n")

    console.print(
        Panel(
            "[bold]Available Commands[/]\n\n"
            "  [cyan]devlog init[/]                     Initialise the database [dim](run once)[/]\n"
            "  [cyan]devlog today[/]                    Today's activity report\n"
            "  [cyan]devlog week[/]                     This week's summary\n"
            "  [cyan]devlog report[/]                   Full report [dim](--format rich / json / markdown)[/]\n"
            "  [cyan]devlog daemon[/]                   Start background collector\n"
            "  [cyan]devlog daemon --stop[/]            Stop the daemon\n"
            "  [cyan]devlog daemon --status[/]          Check daemon status\n"
            "  [cyan]devlog install-hook[/] [dim]<repo>[/]      Wire git hook into a repo\n\n"
            "[dim]Run [bold]devlog --help[/] or [bold]devlog <command> --help[/] for full usage.[/]",
            title=f"[bold green]devlog v{__version__}[/]",
            border_style="cyan",
            padding=(1, 3),
        )
    )


def _version_callback(value: bool):
    if value:
        typer.echo(f"devlog version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=_version_callback, is_eager=True,
        help="Show version and exit."
    ),
):
    """Dev Activity Logger — track your coding activity automatically."""
    # Only show welcome when called with no subcommand
    if ctx.invoked_subcommand is None:
        _print_welcome()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def init():
    """Initialise the database (run this once before first use)."""
    cmd_init()


@app.command()
def today(
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Date in YYYY-MM-DD format (default: today)"),
):
    """Show today's development activity report."""
    cmd_today(date)


@app.command()
def week(
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Any date within the target week (default: today)"),
):
    """Show this week's development summary."""
    cmd_week(date)


@app.command()
def report(
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Date in YYYY-MM-DD (default: today)"),
    fmt: str = typer.Option("rich", "--format", "-f", help="Output format: rich | json | markdown"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Write report to this file path"),
):
    """Generate a full development report (daily + weekly)."""
    cmd_report(date, fmt, output)


@app.command("install-hook")
def install_hook(
    repo: str = typer.Argument(..., help="Path to the Git repository"),
):
    """Install the post-commit Git hook into a repository."""
    cmd_install_hook(repo)


@app.command()
def daemon(
    stop: bool = typer.Option(False, "--stop", help="Stop the running daemon."),
    status: bool = typer.Option(False, "--status", help="Show daemon status."),
):
    """Start the devlog daemon in the background (detached).

    \b
    devlog daemon           — start in background
    devlog daemon --stop    — stop the running daemon
    devlog daemon --status  — check if the daemon is running
    """
    from daemon.watcher import launch_background, stop_daemon, status as daemon_status
    from rich.console import Console
    from rich.panel import Panel
    import time

    console = Console()

    if status:
        info = daemon_status()
        if info["running"]:
            console.print(Panel(
                f"[bold green]● Running[/]  PID: [cyan]{info['pid']}[/]",
                title="[bold]devlog daemon status[/]", border_style="green"
            ))
        else:
            console.print(Panel(
                "[bold red]○ Not running[/]",
                title="[bold]devlog daemon status[/]", border_style="red"
            ))
        return

    if stop:
        pid = stop_daemon()
        if pid:
            console.print(f"[bold yellow]⏹  Daemon stopped[/] (was PID [cyan]{pid}[/])")
        else:
            console.print("[yellow]No running daemon found.[/]")
        return

    # Default: start in background
    try:
        pid = launch_background()
        # Give the process a moment to write its PID file
        time.sleep(0.5)
        console.print(Panel(
            f"[bold green]✓ Daemon started in background[/]\n"
            f"PID: [cyan]{pid}[/]\n\n"
            f"Stop with: [bold]devlog daemon --stop[/]\n"
            f"Status:    [bold]devlog daemon --status[/]",
            title="[bold]devlog daemon[/]", border_style="green"
        ))
    except RuntimeError as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
