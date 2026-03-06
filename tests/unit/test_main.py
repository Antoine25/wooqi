# -*- coding: utf-8 -*-

"""
Unit tests for wooqi.__main__
"""

import pytest

from wooqi import __version__
from wooqi.__main__ import main


class FakeProcess:
    """Minimal stand-in for subprocess.CompletedProcess."""

    def __init__(self, returncode=0):
        self.returncode = returncode


class TestMainHelp:
    def test_help_flag(self, capsys):
        main(["--help"])
        out = capsys.readouterr().out
        assert "Wooqi tests sequencer" in out

    def test_h_flag(self, capsys):
        main(["-h"])
        out = capsys.readouterr().out
        assert "Wooqi tests sequencer" in out


class TestMainVersion:
    def test_version_flag(self, capsys):
        main(["--version"])
        assert capsys.readouterr().out.strip() == __version__

    def test_v_flag(self, capsys):
        main(["-v"])
        assert capsys.readouterr().out.strip() == __version__


class TestMainUnknown:
    def test_unknown_command_exits_minus_one(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--unknown"])
        assert exc_info.value.code == -1

    def test_unknown_command_prints_error(self, capsys):
        with pytest.raises(SystemExit):
            main(["--unknown"])
        out = capsys.readouterr().out
        assert "Error" in out


class TestMainSeqConfig:
    def test_seq_config_runs_pytest(self, monkeypatch, capsys):
        """--seq-config should invoke subprocess.run with pytest."""
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return FakeProcess(returncode=0)

        monkeypatch.setattr("wooqi.__main__.subprocess.run", fake_run)
        with pytest.raises(SystemExit) as exc_info:
            main(["--seq-config", "seq.ini", "--sn", "sample"])

        assert exc_info.value.code == 0
        assert calls, "subprocess.run was not called"
        cmd = calls[0]
        assert "pytest" in cmd
        assert "--wooqi" in cmd
        assert "--spec" in cmd

    def test_seq_config_adds_cache_clear_by_default(self, monkeypatch):
        calls = []

        monkeypatch.setattr("wooqi.__main__.subprocess.run", lambda cmd, **kw: (calls.append(cmd), FakeProcess())[1])
        with pytest.raises(SystemExit):
            main(["--seq-config", "seq.ini", "--sn", "sample"])

        assert "--cache-clear" in calls[0]

    def test_seq_config_no_cache_clear_with_ff(self, monkeypatch):
        calls = []

        monkeypatch.setattr("wooqi.__main__.subprocess.run", lambda cmd, **kw: (calls.append(cmd), FakeProcess())[1])
        with pytest.raises(SystemExit):
            main(["--seq-config", "seq.ini", "--sn", "sample", "--ff"])

        assert "--cache-clear" not in calls[0]

    def test_seq_config_forwards_exit_code(self, monkeypatch):
        monkeypatch.setattr("wooqi.__main__.subprocess.run", lambda cmd, **kw: FakeProcess(returncode=1))
        with pytest.raises(SystemExit) as exc_info:
            main(["--seq-config", "seq.ini", "--sn", "sample"])

        assert exc_info.value.code == 1

