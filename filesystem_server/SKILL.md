---
name: filesystem-server
description: Provides sandboxed file and terminal operations. All paths are resolved within ROOT_DIR and cannot escape it.
---

## Tools

### Navigation
- `ls(path?, show_hidden?)` - List directory contents
- `tree(path?, depth?)` - Recursive directory tree (default depth: 3)
- `file_glob_search(pattern)` - Find files by glob pattern (max 200 results)

### Reading
- `read_file(path)` - Read full file contents
- `read_file_range(path, start_line, end_line)` - Read a line range (1-indexed, inclusive)
- `grep_search(pattern, path?, glob?)` - Regex search across files (max 200 matches)

### Writing
- `create_new_file(path, content)` - Create a new file (fails if it already exists)
- `write_file(path, content)` - Write or overwrite a file
- `single_find_and_replace(path, find, replace, occurrence?)` - Replace the nth occurrence of a string
- `create_directory(path)` - Create a directory (including parents)
- `delete_file(path, confirm=True)` - Delete a file

### Utilities
- `view_diff(path_a, path_b_or_content)` - Unified diff between two files or a file and a string
- `run_terminal_command(command, timeout?)` - Run an allowlisted shell command (default timeout: 30s, max: 120s)
