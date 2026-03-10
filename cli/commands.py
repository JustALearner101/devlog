"""
CLI command implementations — all Typer commands live here.
Imported and registered by cli/main.py.
"""

import json
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

from db.database import init_db
from processor.analytics import get_daily_summary, get_weekly_summary, top_commands

console = Console()


# ---------------------------------------------------------------------------
# devlog init
# ---------------------------------------------------------------------------

def cmd_init():
    """Initialise the database (create tables)."""
    init_db()
    console.print(
        Panel(
            "[bold green]✓[/] Database initialised successfully.\n"
            f"Database file: [cyan]{Path('devlog.db').resolve()}[/]",
            title="[bold]devlog init[/]",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# devlog today
# ---------------------------------------------------------------------------

def cmd_today(report_date: Optional[str] = None):
    """Print the daily development report (defaults to today)."""
    try:
        d = date.fromisoformat(report_date) if report_date else date.today()
    except ValueError:
        console.print(f"[red]Invalid date format: {report_date}. Use YYYY-MM-DD.[/]")
        raise typer.Exit(1)

    summary = get_daily_summary(d)
    cmds = top_commands(d)

    # Header
    console.print()
    console.print(
        Panel(
            f"[bold cyan]Dev Activity Report — {summary['date']}[/]",
            border_style="cyan",
        )
    )

    # Coding Activity table
    activity_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    activity_table.add_column("Metric", style="bold")
    activity_table.add_column("Value", justify="right", style="yellow")
    activity_table.add_row("Commits", str(summary["commits"]))
    activity_table.add_row("Commands Executed", str(summary["commands"]))
    activity_table.add_row("Errors Encountered", str(summary["errors"]))
    console.print(Panel(activity_table, title="[bold]Coding Activity[/]", border_style="blue"))

    # Top Files Modified
    if summary["top_files"]:
        files_table = Table(box=box.SIMPLE, show_header=True, padding=(0, 2))
        files_table.add_column("File", style="cyan")
        files_table.add_column("Changes", justify="right", style="yellow")
        for fname, count in summary["top_files"]:
            files_table.add_row(fname, str(count))
        console.print(Panel(files_table, title="[bold]Top Files Modified[/]", border_style="blue"))
    else:
        console.print(Panel("[dim]No file changes recorded.[/]", title="[bold]Top Files Modified[/]", border_style="blue"))

    # Top Commands
    if cmds:
        cmd_table = Table(box=box.SIMPLE, show_header=True, padding=(0, 2))
        cmd_table.add_column("Command", style="cyan")
        cmd_table.add_column("Count", justify="right", style="yellow")
        for cmd, count in cmds:
            cmd_table.add_row(cmd, str(count))
        console.print(Panel(cmd_table, title="[bold]Top Commands Used[/]", border_style="blue"))

    # Common Errors
    if summary["common_errors"]:
        err_table = Table(box=box.SIMPLE, show_header=True, padding=(0, 2))
        err_table.add_column("Error", style="red")
        err_table.add_column("Count", justify="right", style="yellow")
        for err, count in summary["common_errors"]:
            err_table.add_row(err, str(count))
        console.print(Panel(err_table, title="[bold]Common Errors[/]", border_style="red"))
    else:
        console.print(Panel("[dim green]No errors recorded today![/]", title="[bold]Common Errors[/]", border_style="green"))

    console.print()


# ---------------------------------------------------------------------------
# devlog week
# ---------------------------------------------------------------------------

def cmd_week(report_date: Optional[str] = None):
    """Print the weekly development summary."""
    try:
        d = date.fromisoformat(report_date) if report_date else date.today()
    except ValueError:
        console.print(f"[red]Invalid date format: {report_date}. Use YYYY-MM-DD.[/]")
        raise typer.Exit(1)

    summary = get_weekly_summary(d)

    console.print()
    console.print(
        Panel(
            f"[bold cyan]Weekly Development Summary — {summary['week_start']} to {summary['week_end']}[/]",
            border_style="cyan",
        )
    )

    week_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    week_table.add_column("Metric", style="bold")
    week_table.add_column("Value", justify="right", style="yellow")
    week_table.add_row("Total Commits", str(summary["total_commits"]))
    week_table.add_row("Total Commands", str(summary["total_commands"]))
    week_table.add_row("Total Coding Sessions", str(summary["total_coding_sessions"]))
    week_table.add_row("Errors", str(summary["total_errors"]))
    week_table.add_row("Most Active Day", summary["most_active_day"])
    week_table.add_row("Most Worked Module", summary["most_worked_module"])
    console.print(Panel(week_table, title="[bold]Weekly Stats[/]", border_style="blue"))
    console.print()


# ---------------------------------------------------------------------------
# devlog report
# ---------------------------------------------------------------------------

def cmd_report(
    report_date: Optional[str] = None,
    fmt: str = "rich",
    output: Optional[str] = None,
):
    """
    Generate a development report.

    --fmt: rich (default) | json | markdown
    --output: file path to write the report (optional)
    """
    try:
        d = date.fromisoformat(report_date) if report_date else date.today()
    except ValueError:
        console.print(f"[red]Invalid date format: {report_date}. Use YYYY-MM-DD.[/]")
        raise typer.Exit(1)

    daily = get_daily_summary(d)
    weekly = get_weekly_summary(d)
    cmds = top_commands(d)

    if fmt == "json":
        data = {"daily": daily, "weekly": weekly, "top_commands": cmds}
        result = json.dumps(data, indent=2)
        if output:
            Path(output).write_text(result, encoding="utf-8")
            console.print(f"[green]Report written to {output}[/]")
        else:
            print(result)
        return

    if fmt == "markdown":
        lines = [
            f"# Dev Activity Report — {daily['date']}",
            "",
            "## Coding Activity",
            f"- **Commits:** {daily['commits']}",
            f"- **Commands Executed:** {daily['commands']}",
            f"- **Errors Encountered:** {daily['errors']}",
            "",
            "## Top Files Modified",
        ]
        for fname, cnt in daily["top_files"]:
            lines.append(f"- `{fname}` ({cnt})")
        lines += [
            "",
            "## Top Commands Used",
        ]
        for cmd, cnt in cmds:
            lines.append(f"- `{cmd}` ({cnt})")
        lines += [
            "",
            "## Common Errors",
        ]
        for err, cnt in daily["common_errors"]:
            lines.append(f"- {err} ({cnt})")
        lines += [
            "",
            f"## Weekly Summary ({weekly['week_start']} – {weekly['week_end']})",
            f"- **Total Commits:** {weekly['total_commits']}",
            f"- **Total Commands:** {weekly['total_commands']}",
            f"- **Total Sessions:** {weekly['total_coding_sessions']}",
            f"- **Errors:** {weekly['total_errors']}",
            f"- **Most Active Day:** {weekly['most_active_day']}",
            f"- **Most Worked Module:** {weekly['most_worked_module']}",
        ]
        result = "\n".join(lines)
        if output:
            Path(output).write_text(result, encoding="utf-8")
            console.print(f"[green]Report written to {output}[/]")
        else:
            print(result)
        return

    # Default: Rich
    cmd_today(report_date)
    cmd_week(report_date)


# ---------------------------------------------------------------------------
# devlog install-hook
# ---------------------------------------------------------------------------

def cmd_install_hook(repo: str):
    """Install the Git post-commit hook into the specified repository."""
    from collector.git_collector import install_git_hook

    try:
        install_git_hook(repo)
        console.print(f"[bold green]✓[/] Git hook installed in [cyan]{repo}[/]")
    except Exception as e:
        console.print(f"[red]Error installing hook: {e}[/]")
        raise typer.Exit(1)

