"""Core sync engine - reads config and executes a unified sequence."""

import os
import shutil

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config_sync.utils import (
    confirm_continue,
    confirm_overwrite_dir,
    confirm_overwrite_file,
    run_command,
    run_command_interactive,
)

console = Console()

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "config.yaml",
)


def load_config(config_path: str | None = None) -> dict:
    """Load and return the YAML config file."""
    path = config_path or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def resolve_work_dir(config: dict, config_path: str | None = None) -> str:
    """Resolve work_dir relative to cwd, or use absolute."""
    value = config.get("work_dir", ".")
    if os.path.isabs(value):
        return value
    return os.path.abspath(value)


def expand_dst(dst: str) -> str:
    """Expand ~ and environment variables in a destination path."""
    return os.path.expanduser(os.path.expandvars(dst))


def print_step_header(index: int, total: int, action: str, name: str) -> None:
    """Print a styled step header."""
    label = f"[bold white][{index}/{total}][/bold white] [bold cyan]{action}[/bold cyan] [bold]{name}[/bold]"
    console.print(Panel(label, border_style="blue", padding=(0, 1)))


# ─── File copy helpers ────────────────────────────────────────────────────────


def _copy_file(src_path: str, dst_path: str, force: bool) -> bool:
    """Copy a single file from src to dst. Show dst content if it exists."""
    if os.path.exists(dst_path) and not force:
        if not confirm_overwrite_file(dst_path):
            console.print("  [yellow]Skipped[/yellow]")
            return False

    parent = os.path.dirname(dst_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    shutil.copy2(src_path, dst_path)
    console.print(f"  [green]Copied:[/green] {src_path} -> {dst_path}")
    return True


def _copy_dir_overlay(src_path: str, dst_path: str, force: bool) -> bool:
    """Overlay src directory onto dst: only replace files that exist in src.

    Files in dst that don't exist in src are preserved.
    For each file in src, show the existing dst file content before overwriting.
    """
    # Collect files to copy
    files_to_copy = []
    for root, _, files in os.walk(src_path):
        for fname in sorted(files):
            rel = os.path.relpath(os.path.join(root, fname), src_path)
            files_to_copy.append(rel)

    if not files_to_copy:
        console.print("  [dim]No files in source directory[/dim]")
        return False

    # Check which files need user confirmation
    overwrite_map = {}
    if not force and os.path.exists(dst_path):
        overwrite_map = confirm_overwrite_dir(dst_path, src_path)

    copied = 0
    skipped = 0
    for rel in files_to_copy:
        src_file = os.path.join(src_path, rel)
        dst_file = os.path.join(dst_path, rel)

        # Skip if user said no
        if rel in overwrite_map and not overwrite_map[rel]:
            console.print(f"    [yellow]Skipped:[/yellow] {rel}")
            skipped += 1
            continue

        parent = os.path.dirname(dst_file)
        if parent:
            os.makedirs(parent, exist_ok=True)

        shutil.copy2(src_file, dst_file)
        copied += 1

    console.print(f"  [green]Copied {copied} file(s)[/green] to {dst_path}")
    if skipped:
        console.print(f"  [yellow]Skipped {skipped} file(s)[/yellow]")
    return True


# ─── Action: copy ─────────────────────────────────────────────────────────────


def run_copy(
    step: dict,
    work_dir: str,
    dry_run: bool = False,
    force: bool = False,
) -> bool:
    """Copy src -> dst with optional pre_install and post_check."""
    name = step.get("name", "unnamed")
    src = step.get("src")
    dst = step.get("dst")
    pre_install = step.get("pre_install")
    post_check = step.get("post_check")

    if not src or not dst:
        console.print(f"  [red]Error: copy step '{name}' requires src and dst[/red]")
        return False

    src_path = src if os.path.isabs(src) else os.path.join(work_dir, src)
    dst_path = expand_dst(dst)

    # pre_install
    if pre_install:
        if dry_run:
            console.print(f"  [yellow]Would run pre_install:[/yellow] {pre_install}")
        else:
            console.print(f"  [dim]$ {pre_install}[/dim]")
            success, _ = run_command_interactive(pre_install, cwd=work_dir)
            if not success:
                if not confirm_continue(name):
                    console.print("  [yellow]Skipped by user[/yellow]")
                    return False

    # copy
    if not os.path.exists(src_path):
        console.print(f"  [red]Source not found, skipping:[/red] {src_path}")
        return False

    if dry_run:
        console.print(f"  [yellow]Would copy:[/yellow] {src_path} -> {dst_path}")
    else:
        if os.path.isdir(src_path):
            _copy_dir_overlay(src_path, dst_path, force)
        else:
            _copy_file(src_path, dst_path, force)

    # post_check
    if post_check:
        if dry_run:
            console.print(f"  [yellow]Would run post_check:[/yellow] {post_check}")
        else:
            console.print(f"  [dim]$ {post_check}[/dim]")
            run_command_interactive(post_check, cwd=work_dir)

    return True


# ─── Action: append ───────────────────────────────────────────────────────────


def run_append(
    step: dict,
    work_dir: str,
    dry_run: bool = False,
) -> bool:
    """Append contents of src file to dst file."""
    name = step.get("name", "unnamed")
    src = step.get("src")
    dst = step.get("dst")

    if not src or not dst:
        console.print(f"  [red]Error: append step '{name}' requires src and dst[/red]")
        return False

    src_path = src if os.path.isabs(src) else os.path.join(work_dir, src)
    dst_path = expand_dst(dst)

    if not os.path.exists(src_path):
        console.print(f"  [red]Source not found, skipping:[/red] {src_path}")
        return False

    if dry_run:
        console.print(f"  [yellow]Would append:[/yellow] {src_path} >> {dst_path}")
        return True

    with open(src_path, "r") as f:
        content = f.read()

    parent = os.path.dirname(dst_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(dst_path, "a") as f:
        f.write(content)

    console.print(f"  [green]Appended:[/green] {src_path} >> {dst_path}")
    return True


# ─── Action: exe_bash ─────────────────────────────────────────────────────────


def run_exe_bash(
    step: dict,
    work_dir: str,
    dry_run: bool = False,
) -> bool:
    """Run a shell command."""
    name = step.get("name", "unnamed")
    command = step.get("command")
    pre_install = step.get("pre_install")

    if not command:
        console.print(f"  [red]Error: exe_bash step '{name}' requires command[/red]")
        return False

    # pre_install
    if pre_install:
        if dry_run:
            console.print(f"  [yellow]Would run pre_install:[/yellow] {pre_install}")
        else:
            console.print(f"  [dim]$ {pre_install}[/dim]")
            success, _ = run_command_interactive(pre_install, cwd=work_dir)
            if not success:
                if not confirm_continue(name):
                    console.print("  [yellow]Skipped by user[/yellow]")
                    return False

    if dry_run:
        console.print(f"  [yellow]Would run:[/yellow] {command}")
        return True

    console.print(f"  [dim]$ {command}[/dim]")
    return run_command(command, cwd=work_dir)


# ─── Dispatcher ───────────────────────────────────────────────────────────────

ACTION_HANDLERS = {
    "copy": lambda step, wk, dry, force: run_copy(step, wk, dry, force),
    "append": lambda step, wk, dry, force: run_append(step, wk, dry),
    "exe_bash": lambda step, wk, dry, force: run_exe_bash(step, wk, dry),
}


def run_sync(
    config_path: str | None = None,
    only: list[str] | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """Execute the sequence defined in config."""
    config = load_config(config_path)
    work_dir = resolve_work_dir(config, config_path)
    sequence = config.get("sequence", [])

    if not sequence:
        console.print("[yellow]No sequence defined in config.[/yellow]")
        return

    # Banner
    console.print()
    console.print(Panel(
        f"[bold]config-sync[/bold]\n"
        f"[dim]work_dir:[/dim] {work_dir}"
        + ("\n[bold yellow]DRY RUN[/bold yellow] - no files will be modified" if dry_run else ""),
        border_style="green" if not dry_run else "yellow",
    ))

    total = len(sequence) if not only else sum(1 for s in sequence if s.get("name") in only)
    step_num = 0

    for step in sequence:
        action = step.get("action")
        name = step.get("name", "unnamed")

        if only and name not in only:
            continue

        step_num += 1
        print_step_header(step_num, total, action, name)

        handler = ACTION_HANDLERS.get(action)
        if not handler:
            console.print(f"  [red]Unknown action: {action}[/red]")
            continue

        handler(step, work_dir, dry_run, force)

    console.print()
    console.print(Panel("[bold green]Done![/bold green]", border_style="green"))


def list_sequence(config_path: str | None = None) -> None:
    """Print the sequence as a styled table."""
    config = load_config(config_path)
    sequence = config.get("sequence", [])

    if not sequence:
        console.print("[yellow]No sequence defined in config.[/yellow]")
        return

    table = Table(title="Sequence", show_lines=True, border_style="cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Action", style="bold cyan", width=8)
    table.add_column("Name", style="bold white")
    table.add_column("Details")

    for i, step in enumerate(sequence, 1):
        action = step.get("action", "?")
        name = step.get("name", "unnamed")

        details_parts = []
        if action == "copy":
            src = step.get("src", "?")
            dst = step.get("dst", "?")
            details_parts.append(f"{src} -> {dst}")
            if step.get("pre_install"):
                details_parts.append(f"[dim]pre:[/dim] {step['pre_install']}")
            if step.get("post_check"):
                details_parts.append(f"[dim]post:[/dim] {step['post_check']}")
        elif action == "append":
            src = step.get("src", "?")
            dst = step.get("dst", "?")
            details_parts.append(f"{src} >> {dst}")
        elif action == "exe_bash":
            cmd = step.get("command", "?")
            details_parts.append(cmd)
            if step.get("pre_install"):
                details_parts.append(f"[dim]pre:[/dim] {step['pre_install']}")

        details = "\n".join(details_parts) if details_parts else "[dim]-[/dim]"
        table.add_row(str(i), action, name, details)

    console.print(table)
