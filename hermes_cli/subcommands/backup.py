"""``hermes backup`` subcommand parser.

Extracted verbatim from ``hermes_cli/main.py:main()`` (god-file Phase 2).
Handler injected to avoid importing ``main``.
"""

from __future__ import annotations

from typing import Callable, Optional


def build_backup_parser(
    subparsers,
    *,
    cmd_backup: Callable,
    cmd_webdav_backup: Optional[Callable] = None,
) -> None:
    """Attach the ``backup`` subcommand to ``subparsers``."""
    # =========================================================================
    # backup command
    # =========================================================================
    backup_parser = subparsers.add_parser(
        "backup",
        help="Back up Hermes home directory to a zip file",
        description="Create a zip archive of your entire Hermes configuration, "
        "skills, sessions, and data (excludes the hermes-agent codebase). "
        "Use --quick for a fast snapshot of just critical state files.",
    )
    backup_parser.add_argument(
        "-o",
        "--output",
        help="Output path for the zip file (default: ~/hermes-backup-<timestamp>.zip)",
    )
    backup_parser.add_argument(
        "-q",
        "--quick",
        action="store_true",
        help="Quick snapshot: only critical state files (config, state.db, .env, auth, cron)",
    )
    backup_parser.add_argument(
        "-l", "--label", help="Label for the snapshot (only used with --quick)"
    )
    backup_parser.set_defaults(func=cmd_backup)

    if cmd_webdav_backup is None:
        def cmd_webdav_backup(args) -> None:
            from hermes_cli.webdav_backup import run_webdav_command

            run_webdav_command(args)

    backup_targets = backup_parser.add_subparsers(dest="backup_target")
    webdav = backup_targets.add_parser(
        "webdav",
        help="Upload, browse, and restore full backups with WebDAV",
        description=(
            "Store unencrypted full Hermes backup ZIP files on a configured "
            "WebDAV server. ZIP files include secrets from .env."
        ),
    )
    webdav_commands = webdav.add_subparsers(dest="webdav_command", required=True)

    status = webdav_commands.add_parser(
        "status", help="Show redacted WebDAV and automatic-backup status"
    )
    status.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    webdav_commands.add_parser(
        "test", help="Test MKCOL, PUT, GET, PROPFIND, DELETE, and MOVE"
    )
    webdav_commands.add_parser("upload", help="Create and upload a full backup now")

    list_parser = webdav_commands.add_parser(
        "list", help="List complete restorable backups from every device"
    )
    list_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    restore = webdav_commands.add_parser("restore", help="Restore a complete WebDAV backup")
    restore.add_argument("backup_id", help="Backup ID shown by 'hermes backup webdav list'")
    restore.add_argument(
        "--yes", "-y", action="store_true", help="Skip the destructive restore confirmation"
    )

    for parser in (status, webdav_commands.choices["test"], webdav_commands.choices["upload"], list_parser, restore):
        parser.set_defaults(func=cmd_webdav_backup)
