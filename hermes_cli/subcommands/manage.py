"""``hermes manage`` subcommand and ``hermes-manage`` bootstrap."""

from __future__ import annotations

import sys
from typing import Callable


def build_manage_parser(subparsers, *, cmd_manage: Callable) -> None:
    """Attach the Hermes-Louis management center to ``subparsers``."""
    manage_parser = subparsers.add_parser(
        "manage",
        help="Open the Hermes-Louis management center",
        description=(
            "Manage models, custom providers, Gateway services, logs, diagnostics, "
            "and protected Louis updates from one interface."
        ),
    )
    mode = manage_parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Check for configuration created by the legacy shell manager",
    )
    mode.add_argument(
        "--repair",
        action="store_true",
        help="Safely consolidate legacy per-model provider entries",
    )
    manage_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Apply --repair without an interactive confirmation",
    )
    manage_parser.set_defaults(func=cmd_manage)


def entrypoint() -> None:
    """Route the ``hermes-manage`` console script through the main CLI.

    Importing ``hermes_cli.main`` only after injecting the subcommand preserves
    its early profile handling, so ``hermes-manage -p <profile>`` behaves exactly
    like ``hermes -p <profile> manage``.
    """
    sys.argv.insert(1, "manage")
    from hermes_cli.main import main

    main()
