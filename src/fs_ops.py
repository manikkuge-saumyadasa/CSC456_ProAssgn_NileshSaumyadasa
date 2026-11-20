"""Validate and dispatch filesystem requests for the network server.

Command implementations live in ``fs_commands``. File-lock decisions live in
``lock_policy``. This module connects those pieces and translates operating
system errors into messages the server can return to its client.
"""
from errors import FsError
from fs_commands import HANDLERS, Session, USAGE
from lock_policy import lock_plan


def execute(root, session, cmd, args, delay_ms=0):
    """Validate a command, call its handler, and return displayable output."""
    # Look up the command before reading its usage so unsupported names get a
    # clear error instead of a missing-key exception from either mapping.
    if cmd not in HANDLERS:
        raise FsError(f"unknown command: {cmd}")

    # Each command declares its accepted argument-count range and help syntax.
    min_args, max_args, usage = USAGE[cmd]
    # Reject missing or extra arguments before invoking code that may touch disk.
    if not min_args <= len(args) <= max_args:
        raise FsError(f"usage: {usage}")

    try:
        # Handlers implement command-specific filesystem work; pass through the
        # shared root, session state, parsed arguments, and optional delay.
        return HANDLERS[cmd](root, session, args, delay_ms)
    except FsError:
        raise
    except OSError as error:
        # Convert low-level OS failures into the same client-facing error type,
        # preferring the platform message when available and preserving the cause.
        raise FsError(f"{cmd}: {error.strerror or error}") from error
