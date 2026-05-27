"""CLI interface for config-sync."""

import argparse
import sys

from config_sync import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="config-sync",
        description="Execute a unified config sync sequence.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        help="Path to config.yaml (default: config/config.yaml in project root)",
    )
    parser.add_argument(
        "-o",
        "--only",
        nargs="+",
        default=None,
        help="Only run steps with these names (e.g. --only codex claude)",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Preview changes without writing any files",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Skip overwrite confirmation prompts",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List all sequence steps and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Import here to avoid slow startup for --help/--version
    from config_sync.sync import list_sequence, run_sync

    if args.list:
        list_sequence(args.config)
        sys.exit(0)

    try:
        run_sync(
            config_path=args.config,
            only=args.only,
            dry_run=args.dry_run,
            force=args.force,
        )
    except FileNotFoundError as e:
        from rich.console import Console
        Console().print(f"[red]Error: {e}[/red]")
        sys.exit(1)
