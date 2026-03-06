"""Path resolution and sandboxing utilities.

All file operations must go through resolve_path() to ensure paths
stay within the ROOT_DIR sandbox.
"""

import os
from pathlib import Path

from fastmcp.exceptions import ToolError


def get_root_dir() -> Path:
    """Return the sandbox root directory from ROOT_DIR env var, defaulting to cwd."""
    root = os.environ.get("ROOT_DIR", ".")
    return Path(root).resolve()


def resolve_path(path_str: str) -> Path:
    """Resolve a user-provided path against ROOT_DIR.

    Raises ToolError if the resolved path escapes the sandbox.
    """
    root = get_root_dir()
    resolved = (root / path_str).resolve()
    if not resolved.is_relative_to(root):
        raise ToolError(
            f"Path '{path_str}' resolves outside the allowed root directory."
        )
    return resolved
