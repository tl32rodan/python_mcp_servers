"""Path resolution utilities.

Resolves user-provided paths to absolute paths. Supports both relative
(resolved against cwd) and absolute paths.
"""

from pathlib import Path


def resolve_path(path_str: str) -> Path:
    """Resolve a user-provided path to an absolute path.

    Accepts both relative paths (resolved against cwd) and absolute paths.
    """
    return Path(path_str).resolve()
