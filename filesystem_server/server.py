"""MCP Filesystem & Terminal Server.

A Python MCP server providing file navigation, reading, writing, and
terminal command execution.
"""

import difflib
import fnmatch
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from filesystem_server.path_utils import resolve_path

mcp = FastMCP("Filesystem & Terminal")

# ---------------------------------------------------------------------------
# Default allowed commands for run_terminal_command
# ---------------------------------------------------------------------------
_DEFAULT_ALLOWED_CMDS = (
    "python,pytest,git,ls,cat,grep,rg,find,echo,pip,head,tail,"
    "wc,sort,uniq,diff,cd,pwd,env,mkdir,cp,mv,touch,rm,chmod,"
    "sed,awk,curl,wget,tar,zip,unzip,which,date,whoami"
)


def _allowed_commands() -> set[str]:
    raw = os.environ.get("ALLOWED_CMDS", _DEFAULT_ALLOWED_CMDS)
    return {cmd.strip() for cmd in raw.split(",") if cmd.strip()}


# ===================================================================
# Navigation & Orientation
# ===================================================================


@mcp.tool()
def ls(
    path: Annotated[str, Field(description="Directory path (relative or absolute)")] = ".",
    show_hidden: Annotated[bool, Field(description="Include hidden files/dirs")] = False,
) -> str:
    """List files and directories at the given path."""
    resolved = resolve_path(path)
    if not resolved.is_dir():
        raise ToolError(f"'{path}' is not a directory.")

    entries: list[str] = []
    try:
        for entry in sorted(resolved.iterdir(), key=lambda e: e.name.lower()):
            name = entry.name
            if not show_hidden and name.startswith("."):
                continue
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{name}{suffix}")
    except PermissionError:
        raise ToolError(f"Permission denied: '{path}'")

    if not entries:
        return "(empty directory)"
    return "\n".join(entries)


@mcp.tool()
def tree(
    path: Annotated[str, Field(description="Directory path (relative or absolute)")] = ".",
    max_depth: Annotated[int, Field(description="Maximum depth to recurse")] = 3,
) -> str:
    """Show a recursive directory tree up to max_depth levels."""
    resolved = resolve_path(path)
    if not resolved.is_dir():
        raise ToolError(f"'{path}' is not a directory.")

    lines: list[str] = [resolved.name + "/"]

    def _walk(dir_path: Path, prefix: str, depth: int) -> None:
        if depth >= max_depth:
            return
        try:
            children = sorted(dir_path.iterdir(), key=lambda e: e.name.lower())
        except PermissionError:
            return
        # Filter hidden at depth > 0
        children = [c for c in children if not c.name.startswith(".")]
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            suffix = "/" if child.is_dir() else ""
            lines.append(f"{prefix}{connector}{child.name}{suffix}")
            if child.is_dir():
                extension = "    " if is_last else "│   "
                _walk(child, prefix + extension, depth + 1)

    _walk(resolved, "", 0)
    return "\n".join(lines)


@mcp.tool()
def file_glob_search(
    pattern: Annotated[str, Field(description="Glob pattern, e.g. '**/*.py'")],
    path: Annotated[str, Field(description="Directory to search from")] = ".",
) -> str:
    """Find files matching a glob pattern. Returns matched file paths."""
    resolved = resolve_path(path)
    if not resolved.is_dir():
        raise ToolError(f"'{path}' is not a directory.")

    matches: list[str] = []
    for match in resolved.glob(pattern):
        if match.is_file():
            matches.append(str(match))
            if len(matches) >= 200:
                break

    if not matches:
        return "No files matched the pattern."
    matches.sort()
    result = "\n".join(matches)
    if len(matches) == 200:
        result += "\n(results truncated at 200 matches)"
    return result


# ===================================================================
# Reading
# ===================================================================


@mcp.tool()
def read_file(
    path: Annotated[str, Field(description="File path (relative or absolute)")],
) -> str:
    """Read the full content of a text file."""
    resolved = resolve_path(path)
    if not resolved.is_file():
        raise ToolError(f"'{path}' is not a file or does not exist.")
    try:
        return resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ToolError(f"'{path}' appears to be a binary file and cannot be read as text.")


@mcp.tool()
def read_file_range(
    path: Annotated[str, Field(description="File path (relative or absolute)")],
    start_line: Annotated[int, Field(description="Start line number (1-indexed)")],
    end_line: Annotated[int, Field(description="End line number (inclusive)")],
) -> str:
    """Read a specific range of lines from a file (1-indexed, inclusive)."""
    resolved = resolve_path(path)
    if not resolved.is_file():
        raise ToolError(f"'{path}' is not a file or does not exist.")
    if start_line < 1:
        raise ToolError("start_line must be >= 1.")
    if end_line < start_line:
        raise ToolError("end_line must be >= start_line.")

    try:
        all_lines = resolved.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        raise ToolError(f"'{path}' appears to be a binary file.")

    total = len(all_lines)
    if start_line > total:
        raise ToolError(f"start_line {start_line} exceeds file length ({total} lines).")

    end = min(end_line, total)
    selected = all_lines[start_line - 1 : end]
    numbered = [f"{start_line + i:>6}\t{line}" for i, line in enumerate(selected)]
    return "\n".join(numbered)


@mcp.tool()
def grep_search(
    pattern: Annotated[str, Field(description="Regex pattern to search for")],
    path: Annotated[str, Field(description="Directory or file to search in")] = ".",
    include_glob: Annotated[str | None, Field(description="Glob to filter filenames, e.g. '*.py'")] = None,
) -> str:
    """Search file contents by regex pattern. Returns matching lines with file paths and line numbers."""
    resolved = resolve_path(path)

    try:
        regex = re.compile(pattern)
    except re.error as e:
        raise ToolError(f"Invalid regex pattern: {e}")

    matches: list[str] = []

    def _search_file(file_path: Path) -> None:
        try:
            text = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            return
        for line_num, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                matches.append(f"{file_path}:{line_num}: {line}")
                if len(matches) >= 200:
                    return

    if resolved.is_file():
        _search_file(resolved)
    elif resolved.is_dir():
        for dirpath, _dirnames, filenames in os.walk(resolved):
            dp = Path(dirpath)
            # Skip hidden directories
            if any(part.startswith(".") for part in dp.relative_to(resolved).parts):
                continue
            for fname in sorted(filenames):
                if fname.startswith("."):
                    continue
                if include_glob and not fnmatch.fnmatch(fname, include_glob):
                    continue
                _search_file(dp / fname)
                if len(matches) >= 200:
                    break
            if len(matches) >= 200:
                break
    else:
        raise ToolError(f"'{path}' does not exist.")

    if not matches:
        return "No matches found."
    result = "\n".join(matches)
    if len(matches) == 200:
        result += "\n(results truncated at 200 matches)"
    return result


# ===================================================================
# Writing & Editing
# ===================================================================


@mcp.tool()
def create_new_file(
    path: Annotated[str, Field(description="File path (relative or absolute)")],
    content: Annotated[str, Field(description="Content to write")],
) -> str:
    """Create a new file. Fails if the file already exists."""
    resolved = resolve_path(path)
    if resolved.exists():
        raise ToolError(f"'{path}' already exists.")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return f"Created: {path}"


@mcp.tool()
def write_file_range(
    path: Annotated[str, Field(description="File path (relative or absolute)")],
    content: Annotated[str, Field(description="New content for the specified line range")],
    start_line: Annotated[int, Field(description="Start line number (1-indexed)")],
    end_line: Annotated[int, Field(description="End line number (inclusive, replaced with new content)")],
) -> str:
    """Replace a range of lines in an existing file (1-indexed, inclusive).

    Lines from start_line to end_line are replaced with the provided content.
    The file must already exist.
    """
    resolved = resolve_path(path)
    if not resolved.is_file():
        raise ToolError(f"'{path}' is not a file or does not exist.")
    if start_line < 1:
        raise ToolError("start_line must be >= 1.")
    if end_line < start_line:
        raise ToolError("end_line must be >= start_line.")

    try:
        all_lines = resolved.read_text(encoding="utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        raise ToolError(f"'{path}' appears to be a binary file.")

    total = len(all_lines)
    if start_line > total:
        raise ToolError(f"start_line {start_line} exceeds file length ({total} lines).")

    end = min(end_line, total)

    # Build new content: ensure it ends with newline for proper splicing
    new_lines = content.splitlines(keepends=True)
    if new_lines and not new_lines[-1].endswith("\n"):
        # Preserve trailing newline style from original if last replaced line had one
        if end <= total and all_lines[end - 1].endswith("\n"):
            new_lines[-1] += "\n"

    result_lines = all_lines[: start_line - 1] + new_lines + all_lines[end:]
    resolved.write_text("".join(result_lines), encoding="utf-8")

    # Return context around the edit
    written_count = len(new_lines)
    ctx_start = max(0, start_line - 2)
    ctx_end = min(len(result_lines), start_line - 1 + written_count + 2)
    context = [
        f"{ctx_start + j + 1:>6}\t{result_lines[ctx_start + j].rstrip(chr(10))}"
        for j in range(ctx_end - ctx_start)
    ]
    return (
        f"Replaced lines {start_line}-{end} with {written_count} line(s) in {path}:\n"
        + "\n".join(context)
    )


@mcp.tool()
def single_find_and_replace(
    path: Annotated[str, Field(description="File path (relative or absolute)")],
    find_str: Annotated[str, Field(description="String to find")],
    replace_str: Annotated[str, Field(description="Replacement string")],
    occurrence: Annotated[int, Field(description="Which occurrence to replace (1-indexed)")] = 1,
) -> str:
    """Find the nth occurrence of a string in a file and replace it."""
    resolved = resolve_path(path)
    if not resolved.is_file():
        raise ToolError(f"'{path}' is not a file or does not exist.")
    if occurrence < 1:
        raise ToolError("occurrence must be >= 1.")

    text = resolved.read_text(encoding="utf-8")
    # Find all occurrences
    start = 0
    for i in range(occurrence):
        pos = text.find(find_str, start)
        if pos == -1:
            found = i
            raise ToolError(
                f"Only found {found} occurrence(s) of the search string, "
                f"but occurrence={occurrence} was requested."
            )
        if i < occurrence - 1:
            start = pos + 1

    # Replace the specific occurrence
    new_text = text[:pos] + replace_str + text[pos + len(find_str) :]
    resolved.write_text(new_text, encoding="utf-8")

    # Return context around the replacement
    lines = new_text.splitlines()
    # Find which line the replacement starts on
    char_count = 0
    replace_line = 0
    for idx, line in enumerate(lines):
        char_count += len(line) + 1  # +1 for newline
        if char_count > pos:
            replace_line = idx
            break

    ctx_start = max(0, replace_line - 2)
    ctx_end = min(len(lines), replace_line + 3)
    context_lines = [
        f"{ctx_start + j + 1:>6}\t{lines[ctx_start + j]}"
        for j in range(ctx_end - ctx_start)
    ]
    return f"Replaced occurrence {occurrence} in {path}:\n" + "\n".join(context_lines)


@mcp.tool()
def delete_file(
    path: Annotated[str, Field(description="File path (relative or absolute)")],
    confirm: Annotated[bool, Field(description="Must be true to confirm deletion")] = False,
) -> str:
    """Delete a file. Requires confirm=true as a safety measure."""
    if not confirm:
        raise ToolError("Set confirm=true to actually delete the file.")
    resolved = resolve_path(path)
    if not resolved.is_file():
        raise ToolError(f"'{path}' is not a file or does not exist.")
    resolved.unlink()
    return f"Deleted: {path}"


@mcp.tool()
def create_directory(
    path: Annotated[str, Field(description="Directory path (relative or absolute)")],
) -> str:
    """Create a directory and any missing parent directories."""
    resolved = resolve_path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return f"Directory created: {path}"


# ===================================================================
# Review & Execution
# ===================================================================


@mcp.tool()
def view_diff(
    path_a: Annotated[str, Field(description="First file path (relative or absolute)")],
    path_b_or_content: Annotated[str, Field(description="Second file path or string content")],
    is_content: Annotated[bool, Field(description="If true, treat path_b_or_content as string content")] = False,
) -> str:
    """Show a unified diff between two files, or between a file and a string."""
    resolved_a = resolve_path(path_a)
    if not resolved_a.is_file():
        raise ToolError(f"'{path_a}' is not a file or does not exist.")

    lines_a = resolved_a.read_text(encoding="utf-8").splitlines(keepends=True)
    label_a = path_a

    if is_content:
        lines_b = path_b_or_content.splitlines(keepends=True)
        label_b = "(provided content)"
    else:
        resolved_b = resolve_path(path_b_or_content)
        if not resolved_b.is_file():
            raise ToolError(f"'{path_b_or_content}' is not a file or does not exist.")
        lines_b = resolved_b.read_text(encoding="utf-8").splitlines(keepends=True)
        label_b = path_b_or_content

    diff = difflib.unified_diff(lines_a, lines_b, fromfile=label_a, tofile=label_b)
    result = "".join(diff)
    if not result:
        return "No differences found."
    return result


@mcp.tool()
def run_terminal_command(
    command: Annotated[str, Field(description="Shell command to run")],
    timeout: Annotated[int, Field(description="Timeout in seconds (max 120)")] = 30,
) -> str:
    """Run an allowlisted shell command and return its output."""
    timeout = min(max(timeout, 1), 120)

    try:
        parts = shlex.split(command)
    except ValueError as e:
        raise ToolError(f"Failed to parse command: {e}")

    if not parts:
        raise ToolError("Empty command.")

    base_cmd = os.path.basename(parts[0])
    allowed = _allowed_commands()
    if base_cmd not in allowed:
        raise ToolError(
            f"Command '{base_cmd}' is not in the allowed list. "
            f"Allowed: {', '.join(sorted(allowed))}"
        )

    try:
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"Command timed out after {timeout}s.")
    except FileNotFoundError:
        raise ToolError(f"Command '{base_cmd}' not found on this system.")

    output_parts: list[str] = []
    if result.stdout:
        output_parts.append(result.stdout)
    if result.stderr:
        output_parts.append(f"[stderr]\n{result.stderr}")
    output_parts.append(f"[exit code: {result.returncode}]")
    return "\n".join(output_parts)


# ===================================================================
# Entry point
# ===================================================================

if __name__ == "__main__":
    mcp.run()
