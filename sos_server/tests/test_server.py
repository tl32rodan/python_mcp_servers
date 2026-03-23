"""Tests for the ClioSoft SOS MCP server."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from fastmcp.exceptions import ToolError

from sos_server.server import (
    sos_checkin,
    sos_checkout,
    sos_create,
    sos_populate,
    sos_update_selected,
)


def _mock_result(stdout="", stderr="", returncode=0):
    """Create a mock CompletedProcess."""
    m = MagicMock(spec=subprocess.CompletedProcess)
    m.stdout = stdout
    m.stderr = stderr
    m.returncode = returncode
    return m


# ===================================================================
# sos_create
# ===================================================================


class TestSosCreate:
    @patch("sos_server.server.subprocess.run")
    def test_create_success(self, mock_run):
        mock_run.return_value = _mock_result(stdout="Created foo.v")
        result = sos_create(paths=["foo.v"])
        assert "Created foo.v" in result
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["soscmd", "create", "foo.v"]

    @patch("sos_server.server.subprocess.run")
    def test_create_multiple(self, mock_run):
        mock_run.return_value = _mock_result(stdout="Created 2 objects")
        result = sos_create(paths=["a.v", "b.v"])
        args = mock_run.call_args[0][0]
        assert args == ["soscmd", "create", "a.v", "b.v"]

    def test_create_empty_paths(self):
        with pytest.raises(ToolError, match="At least one path"):
            sos_create(paths=[])

    @patch("sos_server.server.subprocess.run")
    def test_create_failure(self, mock_run):
        mock_run.return_value = _mock_result(
            stderr="Permission denied", returncode=1
        )
        with pytest.raises(ToolError, match="Permission denied"):
            sos_create(paths=["foo.v"])


# ===================================================================
# sos_populate
# ===================================================================


class TestSosPopulate:
    @patch("sos_server.server.subprocess.run")
    def test_populate_success(self, mock_run):
        mock_run.return_value = _mock_result(stdout="Populated rtl/")
        result = sos_populate(paths=["rtl/"])
        assert "Populated" in result
        args = mock_run.call_args[0][0]
        assert args == ["soscmd", "populate", "rtl/"]

    def test_populate_empty_paths(self):
        with pytest.raises(ToolError, match="At least one path"):
            sos_populate(paths=[])

    @patch("sos_server.server.subprocess.run")
    def test_populate_failure(self, mock_run):
        mock_run.return_value = _mock_result(
            stderr="Object not found", returncode=1
        )
        with pytest.raises(ToolError, match="Object not found"):
            sos_populate(paths=["missing/"])


# ===================================================================
# sos_update_selected
# ===================================================================


class TestSosUpdateSelected:
    @patch("sos_server.server.subprocess.run")
    def test_update_no_paths(self, mock_run):
        mock_run.return_value = _mock_result(stdout="Updated 5 objects")
        result = sos_update_selected()
        assert "Updated" in result
        args = mock_run.call_args[0][0]
        assert args == ["soscmd", "updatesel"]

    @patch("sos_server.server.subprocess.run")
    def test_update_with_paths(self, mock_run):
        mock_run.return_value = _mock_result(stdout="Updated rtl/")
        result = sos_update_selected(paths=["rtl/"])
        args = mock_run.call_args[0][0]
        assert args == ["soscmd", "updatesel", "rtl/"]

    @patch("sos_server.server.subprocess.run")
    def test_update_failure(self, mock_run):
        mock_run.return_value = _mock_result(stderr="No workarea", returncode=1)
        with pytest.raises(ToolError, match="No workarea"):
            sos_update_selected()


# ===================================================================
# sos_checkout
# ===================================================================


class TestSosCheckout:
    @patch("sos_server.server.subprocess.run")
    def test_checkout_success(self, mock_run):
        mock_run.return_value = _mock_result(stdout="Checked out alu.v")
        result = sos_checkout(paths=["alu.v"])
        assert "Checked out" in result
        args = mock_run.call_args[0][0]
        assert args == ["soscmd", "co", "alu.v"]

    @patch("sos_server.server.subprocess.run")
    def test_checkout_multiple(self, mock_run):
        mock_run.return_value = _mock_result(stdout="Checked out 2 files")
        result = sos_checkout(paths=["a.v", "b.v"])
        args = mock_run.call_args[0][0]
        assert args == ["soscmd", "co", "a.v", "b.v"]

    def test_checkout_empty_paths(self):
        with pytest.raises(ToolError, match="At least one path"):
            sos_checkout(paths=[])

    @patch("sos_server.server.subprocess.run")
    def test_checkout_failure(self, mock_run):
        mock_run.return_value = _mock_result(
            stderr="Already checked out", returncode=1
        )
        with pytest.raises(ToolError, match="Already checked out"):
            sos_checkout(paths=["alu.v"])


# ===================================================================
# sos_checkin
# ===================================================================


class TestSosCheckin:
    @patch("sos_server.server.subprocess.run")
    def test_checkin_success(self, mock_run):
        mock_run.return_value = _mock_result(stdout="Checked in alu.v")
        result = sos_checkin(paths=["alu.v"], log_message="fix timing")
        assert "Checked in" in result
        args = mock_run.call_args[0][0]
        assert args == ["soscmd", "ci", "-D", '-aLog="fix timing"', "alu.v"]

    @patch("sos_server.server.subprocess.run")
    def test_checkin_empty_log(self, mock_run):
        mock_run.return_value = _mock_result(stdout="Checked in alu.v")
        sos_checkin(paths=["alu.v"])
        args = mock_run.call_args[0][0]
        assert args == ["soscmd", "ci", "-D", '-aLog=""', "alu.v"]

    def test_checkin_empty_paths(self):
        with pytest.raises(ToolError, match="At least one path"):
            sos_checkin(paths=[])

    @patch("sos_server.server.subprocess.run")
    def test_checkin_failure(self, mock_run):
        mock_run.return_value = _mock_result(
            stderr="Not checked out", returncode=1
        )
        with pytest.raises(ToolError, match="Not checked out"):
            sos_checkin(paths=["alu.v"])


# ===================================================================
# Common behavior
# ===================================================================


class TestCommon:
    @patch("sos_server.server.subprocess.run")
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="soscmd", timeout=120)
        with pytest.raises(ToolError, match="timed out"):
            sos_checkout(paths=["alu.v"])

    @patch("sos_server.server.subprocess.run")
    def test_soscmd_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(ToolError, match="not found"):
            sos_checkout(paths=["alu.v"])

    @patch("sos_server.server.subprocess.run")
    def test_custom_sos_cmd(self, mock_run, monkeypatch):
        monkeypatch.setenv("SOS_CMD", "/opt/sos/bin/soscmd")
        mock_run.return_value = _mock_result(stdout="OK")
        sos_checkout(paths=["alu.v"])
        args = mock_run.call_args[0][0]
        assert args[0] == "/opt/sos/bin/soscmd"

    @patch("sos_server.server.subprocess.run")
    def test_empty_stdout_returns_success_message(self, mock_run):
        mock_run.return_value = _mock_result(stdout="")
        result = sos_create(paths=["foo.v"])
        assert "completed successfully" in result
