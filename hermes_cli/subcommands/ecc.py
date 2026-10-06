"""``hermes ecc`` — install the ECC workflow pack into the active Dragon data folder."""

from __future__ import annotations

from typing import Callable

from hermes_cli.subcommands._shared import add_json_flag


def build_ecc_parser(subparsers, *, cmd_ecc: Callable) -> None:
    """Attach the ``ecc`` subcommand (status / install / update / remove)."""
    parser = subparsers.add_parser(
        "ecc",
        help="Install the ECC workflow pack into this Dragon data folder",
        description=(
            "Install, update, or remove the ECC (Everything Claude Code) workflow pack. "
            "Writes skills, rules, and commands into the active Dragon data folder. "
            "Does not add bot seats, Cursor hooks, or Memory Vault."
        ),
    )
    add_json_flag(parser, "Print machine-readable status")
    actions = parser.add_subparsers(dest="ecc_action")

    actions.add_parser("status", help="Show whether ECC Workflows is installed")
    actions.add_parser(
        "install",
        help="Install ECC Workflows (minimal profile: skills, rules, commands)",
    )
    actions.add_parser("update", aliases=["upgrade"], help="Re-run the ECC installer (idempotent)")
    actions.add_parser("remove", aliases=["uninstall"], help="Remove ECC Workflows from this Dragon data folder")
    parser.set_defaults(func=cmd_ecc)
