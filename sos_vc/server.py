"""MCP Server for ClioSoft SOS version control.

Exposes commonly-used soscmd operations (create, populate, updatesel, co, ci)
as MCP tools. All commands are executed via subprocess.
"""

import os
import subprocess
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

mcp = FastMCP("ClioSoft SOS")

_DEFAULT_SOS_CMD = "soscmd"
_DEFAULT_TIMEOUT = 120


def _sos_cmd() -> str:
    """Return the soscmd binary path (configurable via SOS_CMD env var)."""
    return os.environ.get("SOS_CMD", _DEFAULT_SOS_CMD)


def _timeout() -> int:
    """Return the command timeout in seconds (configurable via SOS_TIMEOUT)."""
    try:
        return int(os.environ.get("SOS_TIMEOUT", _DEFAULT_TIMEOUT))
    except ValueError:
        return _DEFAULT_TIMEOUT


def _run(args: list[str]) -> str:
    """Run a soscmd command and return its output.

    Raises ToolError on non-zero exit or timeout.
    """
    cmd = [_sos_cmd()] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=_timeout()
        )
    except subprocess.TimeoutExpired:
        raise ToolError(
            f"Command timed out after {_timeout()}s: {' '.join(cmd)}"
        )
    except FileNotFoundError:
        raise ToolError(
            f"'{_sos_cmd()}' not found. Ensure SOS is installed and on PATH, "
            "or set the SOS_CMD environment variable."
        )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        detail = stderr or stdout or f"exit code {result.returncode}"
        raise ToolError(f"soscmd {args[0]} failed: {detail}")

    return result.stdout.strip() or f"soscmd {args[0]} completed successfully."


# ===================================================================
# SOS Tools
# ===================================================================


@mcp.tool()
def sos_create(
    paths: Annotated[
        list[str],
        Field(description="File or directory paths to add to the SOS project"),
    ],
) -> str:
    """Add new files or directories to the SOS project (soscmd create)."""
    if not paths:
        raise ToolError("At least one path is required.")
    return _run(["create"] + paths)


@mcp.tool()
def sos_populate(
    paths: Annotated[
        list[str],
        Field(description="File or directory paths to populate in the workarea"),
    ],
) -> str:
    """Populate files in the SOS workarea (soscmd populate)."""
    if not paths:
        raise ToolError("At least one path is required.")
    return _run(["populate"] + paths)


@mcp.tool()
def sos_update_selected(
    paths: Annotated[
        list[str],
        Field(
            description="Paths to update; if empty, updates all selected objects"
        ),
    ] = [],
) -> str:
    """Update selected objects to match the current RSO (soscmd updatesel)."""
    return _run(["updatesel"] + paths)


@mcp.tool()
def sos_checkout(
    paths: Annotated[
        list[str],
        Field(description="File paths to check out"),
    ],
) -> str:
    """Check out files from SOS with default locking (soscmd co)."""
    if not paths:
        raise ToolError("At least one path is required.")
    return _run(["co"] + paths)


@mcp.tool()
def sos_checkin(
    paths: Annotated[
        list[str],
        Field(description="File paths to check in"),
    ],
    log_message: Annotated[
        str,
        Field(description="Log message for the checkin"),
    ] = "",
) -> str:
    """Check in files to SOS, deleting local copies after checkin (soscmd ci -D)."""
    if not paths:
        raise ToolError("At least one path is required.")
    return _run(["ci", "-D", f'-aLog="{log_message}"'] + paths)
