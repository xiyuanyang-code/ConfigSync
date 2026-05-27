"""Shared utilities for file display, user confirmation, and command execution."""

import os
import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax

console = Console()


def show_file_content(filepath: str) -> None:
    """Print file content with syntax highlighting."""
    try:
        with open(filepath, "r") as f:
            content = f.read()

        ext = os.path.splitext(filepath)[1].lstrip(".")
        lang_map = {
            "toml": "toml", "json": "json", "yaml": "yaml", "yml": "yaml",
            "sh": "bash", "bashrc": "bash", "py": "python",
        }
        lang = lang_map.get(ext, "text")

        syntax = Syntax(content, lang, theme="monokai", line_numbers=False)
        console.print(Panel(syntax, title=filepath, border_style="dim"))
    except Exception as e:
        console.print(f"  [dim](cannot read: {e})[/dim]")


def confirm_overwrite_file(dst_path: str) -> bool:
    """Show existing destination file content and ask user whether to overwrite."""
    console.print(f"\n[yellow]Target already exists:[/yellow] {dst_path}")
    console.print("  [dim]Current content:[/dim]")
    show_file_content(dst_path)
    return Confirm.ask("Overwrite?", default=False)


def confirm_overwrite_dir(dst_path: str, src_path: str) -> dict[str, bool]:
    """For each file in src that also exists in dst, show dst content and ask.

    Returns a dict mapping relative file paths to whether they should be overwritten.
    Files in dst that don't exist in src are skipped (preserved).
    """
    results = {}
    for root, _, files in os.walk(src_path):
        for fname in sorted(files):
            rel = os.path.relpath(os.path.join(root, fname), src_path)
            dst_file = os.path.join(dst_path, rel)
            if os.path.exists(dst_file):
                console.print(f"\n[yellow]File exists:[/yellow] {rel}")
                console.print("  [dim]Current content:[/dim]")
                show_file_content(dst_file)
                results[rel] = Confirm.ask(f"Overwrite [bold]{rel}[/bold]?", default=False)
            else:
                results[rel] = True  # new file, always copy
    return results


def confirm_continue(step_name: str) -> bool:
    """Ask user whether to continue with a step after seeing pre_install output."""
    return Confirm.ask(f"Continue with [bold]{step_name}[/bold]?", default=True)


def run_command(command: str, cwd: str | None = None) -> bool:
    """Run a shell command, streaming stdout/stderr in real-time."""
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        for line in proc.stdout:
            console.print(f"  [dim]{line.rstrip()}[/dim]")

        proc.wait()

        if proc.returncode != 0:
            console.print(f"  [red]Command failed (exit code {proc.returncode})[/red]")
            return False
        return True

    except Exception as e:
        console.print(f"  [red]Command error: {e}[/red]")
        return False


def run_command_interactive(command: str, cwd: str | None = None) -> tuple[bool, str]:
    """Run a shell command, capture and display output, return (success, output)."""
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        output_lines = []
        for line in proc.stdout:
            stripped = line.rstrip()
            output_lines.append(stripped)
            console.print(f"    [dim]{stripped}[/dim]")

        proc.wait()

        output = "\n".join(output_lines)
        success = proc.returncode == 0

        if not success:
            console.print(f"    [red](exit code {proc.returncode})[/red]")

        return success, output

    except Exception as e:
        console.print(f"    [red]Error: {e}[/red]")
        return False, str(e)
