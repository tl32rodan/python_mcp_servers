"""Tests for the filesystem MCP server tools."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from fastmcp.exceptions import ToolError

from filesystem_server.path_utils import resolve_path
from filesystem_server.server import (
    ls,
    tree,
    file_glob_search,
    read_file,
    read_file_range,
    grep_search,
    create_new_file,
    write_file_range,
    single_find_and_replace,
    delete_file,
    create_directory,
    view_diff,
    run_terminal_command,
)


@pytest.fixture(autouse=True)
def use_tmp_cwd(tmp_path, monkeypatch):
    """Change cwd to tmp_path for every test so relative paths resolve there."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


# -------------------------------------------------------------------
# path_utils tests
# -------------------------------------------------------------------


class TestPathUtils:
    def test_resolve_path_relative(self, tmp_path):
        (tmp_path / "hello.txt").touch()
        result = resolve_path("hello.txt")
        assert result == tmp_path / "hello.txt"

    def test_resolve_path_absolute(self, tmp_path):
        target = tmp_path / "abs_test.txt"
        target.touch()
        result = resolve_path(str(target))
        assert result == target

    def test_resolve_path_subdirectory(self, tmp_path):
        sub = tmp_path / "a" / "b"
        sub.mkdir(parents=True)
        result = resolve_path("a/b")
        assert result == sub

    def test_resolve_path_parent_traversal(self, tmp_path):
        # Parent traversal is now allowed — just resolves to wherever it points
        result = resolve_path("..")
        assert result == tmp_path.parent


# -------------------------------------------------------------------
# Navigation & orientation
# -------------------------------------------------------------------


class TestLs:
    def test_ls_basic(self, tmp_path):
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        (tmp_path / "subdir").mkdir()
        result = ls(".")
        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "subdir/" in result

    def test_ls_hidden_excluded(self, tmp_path):
        (tmp_path / ".hidden").touch()
        (tmp_path / "visible.txt").touch()
        result = ls(".", show_hidden=False)
        assert ".hidden" not in result
        assert "visible.txt" in result

    def test_ls_hidden_included(self, tmp_path):
        (tmp_path / ".hidden").touch()
        result = ls(".", show_hidden=True)
        assert ".hidden" in result

    def test_ls_not_a_dir(self, tmp_path):
        (tmp_path / "file.txt").touch()
        with pytest.raises(ToolError, match="not a directory"):
            ls("file.txt")

    def test_ls_empty(self, tmp_path):
        result = ls(".")
        assert "empty" in result.lower()

    def test_ls_absolute_path(self, tmp_path):
        (tmp_path / "file.txt").touch()
        result = ls(str(tmp_path))
        assert "file.txt" in result


class TestTree:
    def test_tree_basic(self, tmp_path):
        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "b.txt").touch()
        (tmp_path / "c.txt").touch()
        result = tree(".")
        assert "a/" in result
        assert "b.txt" in result
        assert "c.txt" in result

    def test_tree_depth_limit(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "d"
        deep.mkdir(parents=True)
        (deep / "deep.txt").touch()
        result = tree(".", max_depth=2)
        # depth 0=a/, depth 1=b/, depth 2 would not show
        assert "deep.txt" not in result

    def test_tree_not_a_dir(self, tmp_path):
        (tmp_path / "file.txt").touch()
        with pytest.raises(ToolError, match="not a directory"):
            tree("file.txt")


class TestFileGlobSearch:
    def test_glob_finds_files(self, tmp_path):
        (tmp_path / "a.py").touch()
        (tmp_path / "b.txt").touch()
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "c.py").touch()
        result = file_glob_search("**/*.py")
        assert "a.py" in result
        assert "c.py" in result
        assert "b.txt" not in result

    def test_glob_no_matches(self, tmp_path):
        result = file_glob_search("*.xyz")
        assert "No files matched" in result


# -------------------------------------------------------------------
# Reading
# -------------------------------------------------------------------


class TestReadFile:
    def test_read_file(self, tmp_path):
        (tmp_path / "hello.txt").write_text("Hello, world!")
        result = read_file("hello.txt")
        assert result == "Hello, world!"

    def test_read_file_absolute(self, tmp_path):
        target = tmp_path / "abs.txt"
        target.write_text("absolute content")
        result = read_file(str(target))
        assert result == "absolute content"

    def test_read_file_not_found(self):
        with pytest.raises(ToolError, match="not a file"):
            read_file("nonexistent.txt")

    def test_read_binary_file(self, tmp_path):
        (tmp_path / "binary.bin").write_bytes(b"\x00\x01\x02\xff")
        with pytest.raises(ToolError, match="binary"):
            read_file("binary.bin")


class TestReadFileRange:
    def test_read_range(self, tmp_path):
        content = "\n".join(f"Line {i}" for i in range(1, 11))
        (tmp_path / "lines.txt").write_text(content)
        result = read_file_range("lines.txt", 3, 5)
        assert "Line 3" in result
        assert "Line 4" in result
        assert "Line 5" in result
        assert "Line 2" not in result
        assert "Line 6" not in result

    def test_read_range_invalid(self, tmp_path):
        (tmp_path / "f.txt").write_text("one line")
        with pytest.raises(ToolError, match="start_line must be"):
            read_file_range("f.txt", 0, 1)

    def test_read_range_end_before_start(self, tmp_path):
        (tmp_path / "f.txt").write_text("one\ntwo")
        with pytest.raises(ToolError, match="end_line must be"):
            read_file_range("f.txt", 3, 1)

    def test_read_range_beyond_file(self, tmp_path):
        (tmp_path / "f.txt").write_text("one")
        with pytest.raises(ToolError, match="exceeds file length"):
            read_file_range("f.txt", 5, 10)


class TestGrepSearch:
    def test_grep_finds_pattern(self, tmp_path):
        (tmp_path / "code.py").write_text("def hello():\n    return 42\n")
        result = grep_search("return \\d+")
        assert "code.py:2:" in result
        assert "return 42" in result

    def test_grep_no_matches(self, tmp_path):
        (tmp_path / "code.py").write_text("def hello():\n    pass\n")
        result = grep_search("zzzzz_nonexistent")
        assert "No matches" in result

    def test_grep_include_glob(self, tmp_path):
        (tmp_path / "a.py").write_text("match here\n")
        (tmp_path / "b.txt").write_text("match here\n")
        result = grep_search("match", include_glob="*.py")
        assert "a.py" in result
        assert "b.txt" not in result

    def test_grep_invalid_regex(self):
        with pytest.raises(ToolError, match="Invalid regex"):
            grep_search("[invalid")


# -------------------------------------------------------------------
# Writing & Editing
# -------------------------------------------------------------------


class TestCreateNewFile:
    def test_create(self, tmp_path):
        result = create_new_file("new.txt", "content")
        assert "Created" in result
        assert (tmp_path / "new.txt").read_text() == "content"

    def test_create_fails_if_exists(self, tmp_path):
        (tmp_path / "existing.txt").touch()
        with pytest.raises(ToolError, match="already exists"):
            create_new_file("existing.txt", "content")

    def test_create_with_parents(self, tmp_path):
        create_new_file("a/b/c.txt", "nested")
        assert (tmp_path / "a" / "b" / "c.txt").read_text() == "nested"


class TestWriteFileRange:
    def test_replace_middle_lines(self, tmp_path):
        (tmp_path / "f.txt").write_text("line1\nline2\nline3\nline4\nline5\n")
        result = write_file_range("f.txt", "NEW2\nNEW3\n", 2, 3)
        assert "Replaced lines 2-3" in result
        assert (tmp_path / "f.txt").read_text() == "line1\nNEW2\nNEW3\nline4\nline5\n"

    def test_replace_single_line(self, tmp_path):
        (tmp_path / "f.txt").write_text("aaa\nbbb\nccc\n")
        write_file_range("f.txt", "XXX\n", 2, 2)
        assert (tmp_path / "f.txt").read_text() == "aaa\nXXX\nccc\n"

    def test_replace_with_fewer_lines(self, tmp_path):
        (tmp_path / "f.txt").write_text("a\nb\nc\nd\n")
        write_file_range("f.txt", "MERGED\n", 2, 3)
        assert (tmp_path / "f.txt").read_text() == "a\nMERGED\nd\n"

    def test_replace_with_more_lines(self, tmp_path):
        (tmp_path / "f.txt").write_text("a\nb\nc\n")
        write_file_range("f.txt", "X\nY\nZ\n", 2, 2)
        assert (tmp_path / "f.txt").read_text() == "a\nX\nY\nZ\nc\n"

    def test_file_not_found(self):
        with pytest.raises(ToolError, match="not a file"):
            write_file_range("nope.txt", "data", 1, 1)

    def test_start_line_invalid(self, tmp_path):
        (tmp_path / "f.txt").write_text("line\n")
        with pytest.raises(ToolError, match="start_line must be"):
            write_file_range("f.txt", "x", 0, 1)

    def test_end_before_start(self, tmp_path):
        (tmp_path / "f.txt").write_text("a\nb\n")
        with pytest.raises(ToolError, match="end_line must be"):
            write_file_range("f.txt", "x", 3, 1)

    def test_start_beyond_file(self, tmp_path):
        (tmp_path / "f.txt").write_text("one\n")
        with pytest.raises(ToolError, match="exceeds file length"):
            write_file_range("f.txt", "x", 5, 6)


class TestSingleFindAndReplace:
    def test_replace_first(self, tmp_path):
        (tmp_path / "f.txt").write_text("aaa bbb aaa ccc")
        result = single_find_and_replace("f.txt", "aaa", "XXX", 1)
        assert "Replaced occurrence 1" in result
        content = (tmp_path / "f.txt").read_text()
        assert content == "XXX bbb aaa ccc"

    def test_replace_second(self, tmp_path):
        (tmp_path / "f.txt").write_text("aaa bbb aaa ccc")
        single_find_and_replace("f.txt", "aaa", "XXX", 2)
        content = (tmp_path / "f.txt").read_text()
        assert content == "aaa bbb XXX ccc"

    def test_replace_not_found(self, tmp_path):
        (tmp_path / "f.txt").write_text("hello world")
        with pytest.raises(ToolError, match="Only found 0"):
            single_find_and_replace("f.txt", "zzz", "XXX", 1)

    def test_replace_occurrence_too_high(self, tmp_path):
        (tmp_path / "f.txt").write_text("aaa bbb aaa")
        with pytest.raises(ToolError, match="Only found 2"):
            single_find_and_replace("f.txt", "aaa", "XXX", 3)


class TestDeleteFile:
    def test_delete(self, tmp_path):
        (tmp_path / "del.txt").touch()
        result = delete_file("del.txt", confirm=True)
        assert "Deleted" in result
        assert not (tmp_path / "del.txt").exists()

    def test_delete_without_confirm(self, tmp_path):
        (tmp_path / "del.txt").touch()
        with pytest.raises(ToolError, match="confirm=true"):
            delete_file("del.txt", confirm=False)
        assert (tmp_path / "del.txt").exists()

    def test_delete_nonexistent(self):
        with pytest.raises(ToolError, match="not a file"):
            delete_file("nope.txt", confirm=True)


class TestCreateDirectory:
    def test_create_dir(self, tmp_path):
        result = create_directory("newdir")
        assert "created" in result.lower()
        assert (tmp_path / "newdir").is_dir()

    def test_create_nested(self, tmp_path):
        create_directory("a/b/c")
        assert (tmp_path / "a" / "b" / "c").is_dir()

    def test_create_existing_ok(self, tmp_path):
        (tmp_path / "existing").mkdir()
        result = create_directory("existing")
        assert "created" in result.lower()


# -------------------------------------------------------------------
# Review & Execution
# -------------------------------------------------------------------


class TestViewDiff:
    def test_diff_two_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("line1\nline2\n")
        (tmp_path / "b.txt").write_text("line1\nline3\n")
        result = view_diff("a.txt", "b.txt")
        assert "-line2" in result
        assert "+line3" in result

    def test_diff_file_vs_content(self, tmp_path):
        (tmp_path / "a.txt").write_text("hello\n")
        result = view_diff("a.txt", "goodbye\n", is_content=True)
        assert "-hello" in result
        assert "+goodbye" in result

    def test_diff_no_difference(self, tmp_path):
        (tmp_path / "a.txt").write_text("same\n")
        (tmp_path / "b.txt").write_text("same\n")
        result = view_diff("a.txt", "b.txt")
        assert "No differences" in result


class TestRunTerminalCommand:
    def test_allowed_command(self):
        result = run_terminal_command("echo hello")
        assert "hello" in result
        assert "[exit code: 0]" in result

    def test_disallowed_command(self):
        with pytest.raises(ToolError, match="not in the allowed list"):
            run_terminal_command("reboot")

    def test_command_not_found(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_CMDS", "nonexistent_cmd_xyz")
        with pytest.raises(ToolError, match="not found"):
            run_terminal_command("nonexistent_cmd_xyz")

    def test_timeout(self):
        with pytest.raises(ToolError, match="timed out"):
            run_terminal_command("python -c \"import time; time.sleep(10)\"", timeout=1)

    def test_stderr_captured(self):
        result = run_terminal_command("python -c \"import sys; sys.stderr.write('err\\n')\"")
        assert "[stderr]" in result
        assert "err" in result

    def test_custom_allowed_cmds(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_CMDS", "echo")
        result = run_terminal_command("echo works")
        assert "works" in result
        with pytest.raises(ToolError, match="not in the allowed list"):
            run_terminal_command("ls")
