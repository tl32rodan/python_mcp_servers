# Filesystem Server

An MCP server providing sandboxed file operations and terminal access via FastMCP.

## Installation

```bash
cd filesystem_server
pip install -e .
```

## Usage

```bash
# Run with current directory as sandbox root
filesystem-server

# Run with a specific root directory
ROOT_DIR=/path/to/sandbox filesystem-server
```

## Configuration

| Environment Variable | Description | Default |
|---|---|---|
| `ROOT_DIR` | Sandbox root directory for all file operations | `.` (cwd) |
| `ALLOWED_CMDS` | Comma-separated allowlist for `run_terminal_command` | python, pytest, git, ls, cat, grep, … |

## Available Tools

- **ls** / **tree** / **file_glob_search** — Navigate and find files
- **read_file** / **read_file_range** / **grep_search** — Read and search content
- **create_new_file** / **write_file** / **single_find_and_replace** — Create and edit files
- **delete_file** / **create_directory** — Manage files and directories
- **view_diff** — Compare files or content
- **run_terminal_command** — Execute allowlisted shell commands

All file paths are resolved relative to `ROOT_DIR` and sandboxed to prevent escaping the root.
