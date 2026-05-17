"""Tests for tools.tool_output_limits.

Covers:
1. Default values when no config is provided.
2. Config override picks up user-supplied max_bytes / max_lines /
   max_line_length.
3. Malformed values (None, negative, wrong type) fall back to defaults
   rather than raising.
4. Integration: the helpers return what the terminal_tool and
   file_operations call paths will actually consume.

Port-tracking: anomalyco/opencode PR #23770
(feat(truncate): allow configuring tool output truncation limits).
"""

from __future__ import annotations

import json
import shlex
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tools import tool_output_limits as tol


class TestDefaults:
    def test_defaults_match_previous_hardcoded_values(self):
        assert tol.DEFAULT_MAX_BYTES == 50_000
        assert tol.DEFAULT_MAX_LINES == 2000
        assert tol.DEFAULT_MAX_LINE_LENGTH == 2000

    def test_get_limits_returns_defaults_when_config_missing(self):
        with patch("hermes_cli.config.load_config", return_value={}):
            limits = tol.get_tool_output_limits()
        assert limits == {
            "max_bytes": tol.DEFAULT_MAX_BYTES,
            "max_lines": tol.DEFAULT_MAX_LINES,
            "max_line_length": tol.DEFAULT_MAX_LINE_LENGTH,
        }

    def test_get_limits_returns_defaults_when_config_not_a_dict(self):
        # load_config should always return a dict but be defensive anyway.
        with patch("hermes_cli.config.load_config", return_value="not a dict"):
            limits = tol.get_tool_output_limits()
        assert limits["max_bytes"] == tol.DEFAULT_MAX_BYTES

    def test_get_limits_returns_defaults_when_load_config_raises(self):
        def _boom():
            raise RuntimeError("boom")

        with patch("hermes_cli.config.load_config", side_effect=_boom):
            limits = tol.get_tool_output_limits()
        assert limits["max_lines"] == tol.DEFAULT_MAX_LINES


class TestOverrides:
    def test_user_config_overrides_all_three(self):
        cfg = {
            "tool_output": {
                "max_bytes": 100_000,
                "max_lines": 5000,
                "max_line_length": 4096,
            }
        }
        with patch("hermes_cli.config.load_config", return_value=cfg):
            limits = tol.get_tool_output_limits()
        assert limits == {
            "max_bytes": 100_000,
            "max_lines": 5000,
            "max_line_length": 4096,
        }

    def test_partial_override_preserves_other_defaults(self):
        cfg = {"tool_output": {"max_bytes": 200_000}}
        with patch("hermes_cli.config.load_config", return_value=cfg):
            limits = tol.get_tool_output_limits()
        assert limits["max_bytes"] == 200_000
        assert limits["max_lines"] == tol.DEFAULT_MAX_LINES
        assert limits["max_line_length"] == tol.DEFAULT_MAX_LINE_LENGTH

    def test_section_not_a_dict_falls_back(self):
        cfg = {"tool_output": "nonsense"}
        with patch("hermes_cli.config.load_config", return_value=cfg):
            limits = tol.get_tool_output_limits()
        assert limits["max_bytes"] == tol.DEFAULT_MAX_BYTES


class TestCoercion:
    @pytest.mark.parametrize("bad", [None, "not a number", -1, 0, [], {}])
    def test_invalid_values_fall_back_to_defaults(self, bad):
        cfg = {"tool_output": {"max_bytes": bad, "max_lines": bad, "max_line_length": bad}}
        with patch("hermes_cli.config.load_config", return_value=cfg):
            limits = tol.get_tool_output_limits()
        assert limits["max_bytes"] == tol.DEFAULT_MAX_BYTES
        assert limits["max_lines"] == tol.DEFAULT_MAX_LINES
        assert limits["max_line_length"] == tol.DEFAULT_MAX_LINE_LENGTH

    def test_string_integer_is_coerced(self):
        cfg = {"tool_output": {"max_bytes": "75000"}}
        with patch("hermes_cli.config.load_config", return_value=cfg):
            limits = tol.get_tool_output_limits()
        assert limits["max_bytes"] == 75_000


class TestShortcuts:
    def test_individual_accessors_delegate_to_get_tool_output_limits(self):
        cfg = {
            "tool_output": {
                "max_bytes": 111,
                "max_lines": 222,
                "max_line_length": 333,
            }
        }
        with patch("hermes_cli.config.load_config", return_value=cfg):
            assert tol.get_max_bytes() == 111
            assert tol.get_max_lines() == 222
            assert tol.get_max_line_length() == 333

    def test_terminal_max_bytes_uses_tool_output_without_vesta_run(self):
        cfg = {
            "tool_output": {"max_bytes": 75_000},
            "vesta": {
                "retrieval": {
                    "mode": "disciplined",
                    "broad_read_byte_threshold": 12_000,
                }
            },
        }
        with patch("hermes_cli.config.load_config", return_value=cfg), \
             patch("vesta_runtime.get_current_run", return_value=None):
            assert tol.get_terminal_max_bytes() == 75_000

    def test_terminal_max_bytes_uses_vesta_retrieval_cap_for_active_run(self):
        cfg = {
            "tool_output": {"max_bytes": 75_000},
            "vesta": {
                "retrieval": {
                    "mode": "disciplined",
                    "broad_read_byte_threshold": 12_000,
                }
            },
        }
        with patch("hermes_cli.config.load_config", return_value=cfg), \
             patch("vesta_runtime.get_current_run", return_value=object()):
            assert tol.get_terminal_max_bytes() == 12_000
            info = tol.get_terminal_output_limit_info()
        assert info["max_bytes"] == 12_000
        assert info["source"] == "vesta_retrieval"
        assert info["vesta_active"] is True
        assert info["disciplined"] is True

    def test_terminal_max_bytes_tightens_for_small_vesta_context(self, monkeypatch):
        cfg = {
            "tool_output": {"max_bytes": 75_000},
            "vesta": {
                "retrieval": {
                    "mode": "disciplined",
                    "broad_read_byte_threshold": 20_000,
                }
            },
        }
        monkeypatch.setenv("VESTA_CONTEXT_LENGTH_TOKENS", "65536")
        with patch("hermes_cli.config.load_config", return_value=cfg), \
             patch("vesta_runtime.get_current_run", return_value=object()):
            info = tol.get_terminal_output_limit_info()
        assert info["max_bytes"] == 8192
        assert info["source"] == "vesta_context_retrieval"
        assert info["context_length_tokens"] == 65536

    def test_terminal_max_bytes_ignores_vesta_cap_in_permissive_mode(self):
        cfg = {
            "tool_output": {"max_bytes": 75_000},
            "vesta": {
                "retrieval": {
                    "mode": "permissive",
                    "broad_read_byte_threshold": 12_000,
                }
            },
        }
        with patch("hermes_cli.config.load_config", return_value=cfg), \
             patch("vesta_runtime.get_current_run", return_value=object()):
            assert tol.get_terminal_max_bytes() == 75_000

    def test_terminal_tool_adds_vesta_truncation_metadata(self, tmp_path, monkeypatch):
        from tools.terminal_tool import terminal_tool
        from vesta_runtime import create_run, set_current_run

        monkeypatch.setenv("TERMINAL_ENV", "local")
        monkeypatch.setenv("TERMINAL_CWD", str(tmp_path))
        set_current_run(None)
        create_run(
            session_id="session_terminal_limit",
            workspace_path=tmp_path,
            run_id="run_terminal_limit",
        )
        cfg = {
            "tool_output": {"max_bytes": 50_000},
            "vesta": {
                "retrieval": {
                    "mode": "disciplined",
                    "broad_read_byte_threshold": 12_000,
                }
            },
        }
        command = f"{shlex.quote(sys.executable)} -c \"print('x' * 30000)\""

        try:
            with patch("hermes_cli.config.load_config", return_value=cfg):
                result = json.loads(terminal_tool(command=command, timeout=10))
        finally:
            set_current_run(None)

        assert result["exit_code"] == 0
        assert result["truncated"] is True
        assert result["original_chars"] >= 30_000
        assert result["max_chars"] == 12_000
        assert result["omitted_chars"] > 0
        assert "Vesta disciplined retrieval cap" in result["repair_hint"]

    def test_terminal_tool_non_vesta_truncation_keeps_legacy_shape(self, tmp_path, monkeypatch):
        from tools.terminal_tool import terminal_tool
        from vesta_runtime import set_current_run

        monkeypatch.setenv("TERMINAL_ENV", "local")
        monkeypatch.setenv("TERMINAL_CWD", str(tmp_path))
        set_current_run(None)
        cfg = {"tool_output": {"max_bytes": 1000}}
        command = f"{shlex.quote(sys.executable)} -c \"print('x' * 3000)\""

        with patch("hermes_cli.config.load_config", return_value=cfg):
            result = json.loads(terminal_tool(command=command, timeout=10))

        assert result["exit_code"] == 0
        assert "OUTPUT TRUNCATED" in result["output"]
        assert "truncated" not in result
        assert "repair_hint" not in result

    def test_terminal_tool_vesta_large_output_budget_blocks_repeated_chunks(
        self,
        tmp_path,
        monkeypatch,
    ):
        from tools.terminal_tool import terminal_tool
        from vesta_runtime import create_run, set_current_run

        monkeypatch.setenv("TERMINAL_ENV", "local")
        monkeypatch.setenv("TERMINAL_CWD", str(tmp_path))
        set_current_run(None)
        create_run(
            session_id="session_terminal_budget",
            workspace_path=tmp_path,
            run_id="run_terminal_budget",
            context_length=65_536,
        )
        cfg = {
            "tool_output": {"max_bytes": 50_000},
            "vesta": {
                "retrieval": {
                    "mode": "disciplined",
                    "broad_read_byte_threshold": 20_000,
                }
            },
        }
        command = f"{shlex.quote(sys.executable)} -c \"print('x' * 30000)\""

        try:
            with patch("hermes_cli.config.load_config", return_value=cfg):
                results = [
                    json.loads(
                        terminal_tool(
                            command=command,
                            timeout=10,
                            task_id="terminal_budget_test",
                        )
                    )
                    for _ in range(5)
                ]
        finally:
            set_current_run(None)

        assert results[0]["truncated"] is True
        assert results[0]["max_chars"] == 8192
        assert results[-1]["repeat_truncation_limit_exceeded"] is True
        assert results[-1]["output"] == ""
        assert "already received several large terminal evidence payloads" in results[-1]["repair_hint"]

    def test_terminal_tool_vesta_checkpoint_pressure_blocks_output(
        self,
        tmp_path,
        monkeypatch,
    ):
        from tools.terminal_tool import terminal_tool
        from vesta_runtime import create_run, set_current_run

        monkeypatch.setenv("TERMINAL_ENV", "local")
        monkeypatch.setenv("TERMINAL_CWD", str(tmp_path))
        set_current_run(None)
        tol._VESTA_EVIDENCE_COUNT_BY_RUN.clear()
        create_run(
            session_id="session_terminal_checkpoint_pressure",
            workspace_path=tmp_path,
            run_id="run_terminal_checkpoint_pressure",
        )
        cfg = {"vesta": {"retrieval": {"mode": "disciplined"}}}
        command = f"{shlex.quote(sys.executable)} -c \"print('small payload')\""

        try:
            with patch("hermes_cli.config.load_config", return_value=cfg):
                for _ in range(tol.VESTA_CHECKPOINT_RETRIEVAL_LIMIT):
                    assert tol.vesta_evidence_checkpoint_notice("read_file") is None
                result = json.loads(terminal_tool(command=command, timeout=10))
        finally:
            set_current_run(None)

        assert result["vesta_checkpoint_required"] is True
        assert result["source"] == "terminal"
        assert result["output"] == ""
        assert "compact artifact checkpoint" in result["repair_hint"]


class TestDefaultConfigHasSection:
    """The DEFAULT_CONFIG in hermes_cli.config must expose tool_output so
    that ``hermes setup`` and default installs stay in sync with the
    helpers here."""

    def test_default_config_contains_tool_output_section(self):
        from hermes_cli.config import DEFAULT_CONFIG
        assert "tool_output" in DEFAULT_CONFIG
        section = DEFAULT_CONFIG["tool_output"]
        assert isinstance(section, dict)
        assert section["max_bytes"] == tol.DEFAULT_MAX_BYTES
        assert section["max_lines"] == tol.DEFAULT_MAX_LINES
        assert section["max_line_length"] == tol.DEFAULT_MAX_LINE_LENGTH


class TestVestaCheckpointPressure:
    def test_checkpoint_notice_resets_on_new_artifact_progress_then_counts_again(self, tmp_path):
        manifest_path = tmp_path / "artifact-manifest.md"
        manifest_path.write_text("# Artifact Manifest\n", encoding="utf-8")
        run = SimpleNamespace(run_dir=tmp_path / "run", artifact_manifest_path=manifest_path)
        cfg = {"vesta": {"retrieval": {"mode": "disciplined"}}}
        tol._VESTA_EVIDENCE_COUNT_BY_RUN.clear()
        tol._VESTA_ARTIFACT_PROGRESS_BY_RUN.clear()

        with patch("vesta_runtime.get_current_run", return_value=run), \
             patch("hermes_cli.config.load_config", return_value=cfg):
            notices = [
                tol.vesta_evidence_checkpoint_notice("terminal")
                for _ in range(tol.VESTA_CHECKPOINT_RETRIEVAL_LIMIT)
            ]
            notice = tol.vesta_evidence_checkpoint_notice("terminal")

        assert all(item is None for item in notices)
        assert notice["vesta_checkpoint_required"] is True
        assert notice["source"] == "terminal"
        assert notice["evidence_calls_since_checkpoint"] == tol.VESTA_CHECKPOINT_RETRIEVAL_LIMIT + 1
        assert "compact artifact checkpoint" in notice["repair_hint"]

        manifest_path.write_text(
            "# Artifact Manifest\n\nExpected By: `research_artifact_section_write`\n",
            encoding="utf-8",
        )
        with patch("vesta_runtime.get_current_run", return_value=run), \
             patch("hermes_cli.config.load_config", return_value=cfg):
            assert tol.vesta_evidence_checkpoint_notice("read_file") is None
            assert tol._VESTA_EVIDENCE_COUNT_BY_RUN == {}
            notices_after_progress = [
                tol.vesta_evidence_checkpoint_notice("browser_extract")
                for _ in range(tol.VESTA_CHECKPOINT_RETRIEVAL_LIMIT)
            ]
            notice_after_progress = tol.vesta_evidence_checkpoint_notice("browser_extract")
        assert all(item is None for item in notices_after_progress)
        assert notice_after_progress["vesta_checkpoint_required"] is True
        assert notice_after_progress["source"] == "browser_extract"

    def test_runtime_progress_note_resets_checkpoint_pressure(self, tmp_path):
        run = SimpleNamespace(run_dir=tmp_path / "run", artifact_manifest_path=tmp_path / "manifest.md")
        cfg = {"vesta": {"retrieval": {"mode": "disciplined"}}}
        tol._VESTA_EVIDENCE_COUNT_BY_RUN.clear()
        tol._VESTA_ARTIFACT_PROGRESS_BY_RUN.clear()

        with patch("vesta_runtime.get_current_run", return_value=run), \
             patch("hermes_cli.config.load_config", return_value=cfg):
            for _ in range(tol.VESTA_CHECKPOINT_RETRIEVAL_LIMIT):
                assert tol.vesta_evidence_checkpoint_notice("terminal") is None
            assert tol.vesta_evidence_checkpoint_notice("terminal") is not None

            tol.note_vesta_runtime_progress("ledger_append")

            notices_after_progress = [
                tol.vesta_evidence_checkpoint_notice("terminal")
                for _ in range(tol.VESTA_CHECKPOINT_RETRIEVAL_LIMIT)
            ]
            notice_after_progress = tol.vesta_evidence_checkpoint_notice("terminal")

        assert all(item is None for item in notices_after_progress)
        assert notice_after_progress["vesta_checkpoint_required"] is True


class TestIntegrationReadPagination:
    """normalize_read_pagination uses get_max_lines() — verify the plumbing."""

    def test_pagination_limit_clamped_by_config_value(self):
        from tools.file_operations import normalize_read_pagination
        cfg = {"tool_output": {"max_lines": 50}}
        with patch("hermes_cli.config.load_config", return_value=cfg):
            offset, limit = normalize_read_pagination(offset=1, limit=1000)
        # limit should have been clamped to 50 (the configured max_lines)
        assert limit == 50
        assert offset == 1

    def test_pagination_default_when_config_missing(self):
        from tools.file_operations import normalize_read_pagination
        with patch("hermes_cli.config.load_config", return_value={}):
            offset, limit = normalize_read_pagination(offset=10, limit=100000)
        # Clamped to default MAX_LINES (2000).
        assert limit == tol.DEFAULT_MAX_LINES
        assert offset == 10
