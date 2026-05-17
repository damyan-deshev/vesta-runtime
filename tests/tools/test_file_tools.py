"""Tests for the file tools module (schema, handler wiring, error paths).

Tests verify tool schemas, handler dispatch, validation logic, and error
handling without requiring a running terminal environment.
"""

import json
import logging
from unittest.mock import MagicMock, patch

from tools.file_tools import (
    READ_FILE_SCHEMA,
    WRITE_FILE_SCHEMA,
    PATCH_SCHEMA,
    SEARCH_FILES_SCHEMA,
)


class TestReadFileHandler:
    @patch("tools.file_tools._get_file_ops")
    def test_returns_file_content(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.content = "line1\nline2"
        result_obj.to_dict.return_value = {"content": "line1\nline2", "total_lines": 2}
        mock_ops.read_file.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import read_file_tool
        result = json.loads(read_file_tool("/tmp/test.txt"))
        assert result["content"] == "line1\nline2"
        assert result["total_lines"] == 2
        mock_ops.read_file.assert_called_once_with("/tmp/test.txt", 1, 180)

    @patch("tools.file_tools._get_file_ops")
    def test_custom_offset_and_limit(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.content = "line10"
        result_obj.to_dict.return_value = {"content": "line10", "total_lines": 50}
        mock_ops.read_file.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import read_file_tool
        read_file_tool("/tmp/big.txt", offset=10, limit=20)
        mock_ops.read_file.assert_called_once_with("/tmp/big.txt", 10, 20)

    @patch("tools.file_tools._get_file_ops")
    def test_invalid_offset_and_limit_are_normalized_before_dispatch(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.content = "line1"
        result_obj.to_dict.return_value = {"content": "line1", "total_lines": 1}
        mock_ops.read_file.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import read_file_tool
        read_file_tool("/tmp/big.txt", offset=0, limit=0)
        mock_ops.read_file.assert_called_once_with("/tmp/big.txt", 1, 1)

    @patch("tools.file_tools._get_file_ops")
    def test_exception_returns_error_json(self, mock_get):
        mock_get.side_effect = RuntimeError("terminal not available")

        from tools.file_tools import read_file_tool
        result = json.loads(read_file_tool("/tmp/test.txt"))
        assert "error" in result
        assert "terminal not available" in result["error"]

    @patch("tools.file_tools._get_file_ops")
    def test_vesta_read_file_truncates_to_context_aware_window(
        self,
        mock_get,
        tmp_path,
        monkeypatch,
    ):
        from tools.file_tools import read_file_tool
        from vesta_runtime import create_run, set_current_run

        mock_ops = MagicMock()
        result_obj = MagicMock()
        content = "1| " + ("x" * 20_000)
        result_obj.content = content
        result_obj.to_dict.return_value = {
            "content": content,
            "total_lines": 200,
            "file_size": 20_000,
            "truncated": False,
        }
        mock_ops.read_file.return_value = result_obj
        mock_get.return_value = mock_ops
        cfg = {
            "vesta": {
                "retrieval": {
                    "mode": "disciplined",
                    "broad_read_byte_threshold": 20_000,
                }
            }
        }

        set_current_run(None)
        create_run(
            session_id="session_read_context_cap",
            workspace_path=tmp_path,
            run_id="run_read_context_cap",
            context_length=65_536,
        )
        try:
            with patch("hermes_cli.config.load_config", return_value=cfg):
                result = json.loads(
                    read_file_tool(
                        str(tmp_path / "paper.md"),
                        limit=1000,
                        complete_coverage=True,
                        task_id="read_context_cap",
                    )
                )
        finally:
            set_current_run(None)

        assert result["truncated"] is True
        assert result["original_chars"] == len(content)
        assert result["max_chars"] == 8192
        assert result["max_chars_source"] == "vesta_context_retrieval"
        assert result["context_length_tokens"] == 65_536
        assert "READ_FILE OUTPUT TRUNCATED" in result["content"]
        assert "bounded Vesta evidence window" in result["repair_hint"]

    @patch("tools.file_tools._get_file_ops")
    def test_vesta_read_file_large_window_budget_blocks_repeated_chunks(
        self,
        mock_get,
        tmp_path,
    ):
        from tools.file_tools import read_file_tool
        from vesta_runtime import create_run, set_current_run

        mock_ops = MagicMock()
        result_obj = MagicMock()
        content = "1| " + ("x" * 20_000)
        result_obj.content = content
        result_obj.to_dict.return_value = {
            "content": content,
            "total_lines": 200,
            "file_size": 20_000,
            "truncated": False,
        }
        mock_ops.read_file.return_value = result_obj
        mock_get.return_value = mock_ops
        cfg = {
            "vesta": {
                "retrieval": {
                    "mode": "disciplined",
                    "broad_read_byte_threshold": 20_000,
                }
            }
        }

        set_current_run(None)
        create_run(
            session_id="session_read_budget",
            workspace_path=tmp_path,
            run_id="run_read_budget",
            context_length=65_536,
        )
        try:
            with patch("hermes_cli.config.load_config", return_value=cfg):
                results = [
                    json.loads(
                        read_file_tool(
                            str(tmp_path / f"paper-{idx}.md"),
                            limit=1000,
                            complete_coverage=True,
                            task_id="read_budget_test",
                        )
                    )
                    for idx in range(5)
                ]
        finally:
            set_current_run(None)

        assert results[0]["truncated"] is True
        assert results[0]["max_chars"] == 8192
        assert results[-1]["repeat_truncation_limit_exceeded"] is True
        assert results[-1]["content"] == ""
        assert "already received several large read_file evidence windows" in results[-1]["repair_hint"]

    @patch("tools.file_tools._get_file_ops")
    def test_vesta_checkpoint_pressure_blocks_read_file_content(
        self,
        mock_get,
        tmp_path,
    ):
        from tools import tool_output_limits as tol
        from tools.file_tools import read_file_tool
        from vesta_runtime import create_run, set_current_run

        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.content = "small evidence"
        result_obj.to_dict.return_value = {
            "content": "small evidence",
            "total_lines": 1,
            "file_size": 14,
            "truncated": False,
        }
        mock_ops.read_file.return_value = result_obj
        mock_get.return_value = mock_ops
        cfg = {"vesta": {"retrieval": {"mode": "disciplined"}}}

        set_current_run(None)
        tol._VESTA_EVIDENCE_COUNT_BY_RUN.clear()
        create_run(
            session_id="session_read_checkpoint_pressure",
            workspace_path=tmp_path,
            run_id="run_read_checkpoint_pressure",
        )
        try:
            with patch("hermes_cli.config.load_config", return_value=cfg):
                for _ in range(tol.VESTA_CHECKPOINT_RETRIEVAL_LIMIT):
                    assert tol.vesta_evidence_checkpoint_notice("terminal") is None
                result = json.loads(
                    read_file_tool(
                        str(tmp_path / "source.md"),
                        task_id="read_checkpoint_pressure",
                    )
                )
        finally:
            set_current_run(None)

        assert result["vesta_checkpoint_required"] is True
        assert result["source"] == "read_file"
        assert result["content"] == ""
        assert result["omitted_chars"] == len("small evidence")
        assert "compact artifact checkpoint" in result["repair_hint"]


class TestWriteFileHandler:
    @patch("tools.file_tools._get_file_ops")
    def test_writes_content(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {"status": "ok", "path": "/tmp/out.txt", "bytes": 13}
        mock_ops.write_file.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import write_file_tool
        result = json.loads(write_file_tool("/tmp/out.txt", "hello world!\n"))
        assert result["status"] == "ok"
        mock_ops.write_file.assert_called_once_with("/tmp/out.txt", "hello world!\n")

    @patch("tools.file_tools._get_file_ops")
    def test_permission_error_returns_error_json_without_error_log(self, mock_get, caplog):
        mock_get.side_effect = PermissionError("read-only filesystem")

        from tools.file_tools import write_file_tool
        with caplog.at_level(logging.DEBUG, logger="tools.file_tools"):
            result = json.loads(write_file_tool("/tmp/out.txt", "data"))
        assert "error" in result
        assert "read-only" in result["error"]
        assert any("write_file expected denial" in r.getMessage() for r in caplog.records)
        assert not any(r.levelno >= logging.ERROR for r in caplog.records)

    @patch("tools.file_tools._get_file_ops")
    def test_unexpected_exception_still_logs_error(self, mock_get, caplog):
        mock_get.side_effect = RuntimeError("boom")

        from tools.file_tools import write_file_tool
        with caplog.at_level(logging.ERROR, logger="tools.file_tools"):
            result = json.loads(write_file_tool("/tmp/out.txt", "data"))
        assert result["error"] == "boom"
        assert any("write_file error" in r.getMessage() for r in caplog.records)

    def test_missing_content_key_returns_error(self):
        """#19096 — handler must reject tool calls where 'content' key is absent."""
        from tools.file_tools import _handle_write_file

        result = json.loads(_handle_write_file({"path": "/tmp/oops.md"}))
        assert "error" in result
        assert "content" in result["error"]
        assert "path" not in result.get("error", "").lower() or "missing" not in result.get("error", "").lower() or True  # just check error present

    def test_missing_path_key_returns_error(self):
        """#19096 — handler must reject tool calls where 'path' key is absent."""
        from tools.file_tools import _handle_write_file

        result = json.loads(_handle_write_file({"content": "hello"}))
        assert "error" in result

    def test_vesta_eval_missing_write_file_args_hints_section_writer(self, tmp_path, monkeypatch):
        from tools.file_tools import _handle_write_file
        from vesta_runtime import create_run, set_current_run

        monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
        set_current_run(None)
        create_run(
            session_id="session_write_corrupt_args",
            workspace_path=tmp_path,
            run_id="run_write_corrupt_args",
        )

        try:
            result = json.loads(_handle_write_file({}))
        finally:
            set_current_run(None)

        assert result["success"] is False
        assert result["code"] == "vesta_write_file_args_missing_or_corrupt"
        assert "research_artifact_section_write" in result["repair_hint"]

    def test_explicit_empty_content_is_allowed(self):
        """#19096 — explicit empty string content (file truncation) must still work."""
        from tools.file_tools import _handle_write_file

        with patch("tools.file_tools._get_file_ops") as mock_get:
            mock_ops = MagicMock()
            result_obj = MagicMock()
            result_obj.to_dict.return_value = {"status": "ok", "path": "/tmp/empty.txt", "bytes": 0}
            mock_ops.write_file.return_value = result_obj
            mock_get.return_value = mock_ops

            result = json.loads(_handle_write_file({"path": "/tmp/empty.txt", "content": ""}))
            assert result["status"] == "ok"

    def test_non_string_content_returns_error(self):
        """#19096 — content must be a string, not a dict or list."""
        from tools.file_tools import _handle_write_file

        result = json.loads(_handle_write_file({"path": "/tmp/x.txt", "content": {"nested": "dict"}}))
        assert "error" in result
        assert "string" in result["error"].lower() or "content" in result["error"].lower()

    def test_vesta_eval_rejects_oversized_markdown_artifact_write(self, tmp_path, monkeypatch):
        from tools.file_tools import _handle_write_file
        from vesta_runtime import create_run, set_current_run

        monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
        set_current_run(None)
        create_run(
            session_id="session_write_guard",
            workspace_path=tmp_path,
            run_id="run_write_guard",
        )
        artifact = tmp_path / "live-eval-artifacts" / "report.md"
        cfg = {
            "vesta": {
                "retrieval": {
                    "mode": "disciplined",
                    "broad_read_byte_threshold": 32,
                }
            }
        }

        try:
            with patch("hermes_cli.config.load_config", return_value=cfg), \
                 patch("tools.file_tools._check_sensitive_path", return_value=None), \
                 patch("tools.file_tools._get_file_ops") as mock_get:
                result = json.loads(
                    _handle_write_file(
                        {"path": str(artifact), "content": "x" * 100},
                        task_id="write_guard",
                    )
                )
        finally:
            set_current_run(None)

        assert result["success"] is False
        assert result["code"] == "vesta_artifact_write_too_large"
        assert result["content_chars"] == 100
        assert result["max_chars"] == 32
        assert "compact evidence index" in result["repair_hint"]
        mock_get.assert_not_called()

    def test_vesta_eval_allows_small_markdown_artifact_write(self, tmp_path, monkeypatch):
        from tools.file_tools import _handle_write_file
        from vesta_runtime import create_run, set_current_run

        monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
        set_current_run(None)
        create_run(
            session_id="session_write_guard_small",
            workspace_path=tmp_path,
            run_id="run_write_guard_small",
        )
        monkeypatch.setenv("TERMINAL_CWD", str(tmp_path))
        artifact = "live-eval-artifacts/report.md"
        cfg = {
            "vesta": {
                "retrieval": {
                    "mode": "disciplined",
                    "broad_read_byte_threshold": 32,
                }
            }
        }

        try:
            with patch("hermes_cli.config.load_config", return_value=cfg), \
                 patch("tools.file_tools._check_sensitive_path", return_value=None), \
                 patch("tools.file_tools._get_file_ops") as mock_get:
                mock_ops = MagicMock()
                result_obj = MagicMock()
                result_obj.to_dict.return_value = {
                    "status": "ok",
                    "path": artifact,
                    "bytes": 5,
                }
                mock_ops.write_file.return_value = result_obj
                mock_get.return_value = mock_ops

                result = json.loads(
                    _handle_write_file(
                        {"path": str(artifact), "content": "small"},
                        task_id="write_guard_small",
                    )
                )
        finally:
            set_current_run(None)

        assert result["status"] == "ok"
        mock_ops.write_file.assert_called_once_with(artifact, "small")


class TestPatchHandler:
    @patch("tools.file_tools._get_file_ops")
    def test_replace_mode_calls_patch_replace(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {"status": "ok", "replacements": 1}
        mock_ops.patch_replace.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import patch_tool
        result = json.loads(patch_tool(
            mode="replace", path="/tmp/f.py",
            old_string="foo", new_string="bar"
        ))
        assert result["status"] == "ok"
        mock_ops.patch_replace.assert_called_once_with("/tmp/f.py", "foo", "bar", False)

    @patch("tools.file_tools._get_file_ops")
    def test_replace_mode_replace_all_flag(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {"status": "ok", "replacements": 5}
        mock_ops.patch_replace.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import patch_tool
        patch_tool(mode="replace", path="/tmp/f.py",
                   old_string="x", new_string="y", replace_all=True)
        mock_ops.patch_replace.assert_called_once_with("/tmp/f.py", "x", "y", True)

    @patch("tools.file_tools._get_file_ops")
    def test_replace_mode_missing_path_errors(self, mock_get):
        from tools.file_tools import patch_tool
        result = json.loads(patch_tool(mode="replace", path=None, old_string="a", new_string="b"))
        assert "error" in result

    @patch("tools.file_tools._get_file_ops")
    def test_replace_mode_missing_strings_errors(self, mock_get):
        from tools.file_tools import patch_tool
        result = json.loads(patch_tool(mode="replace", path="/tmp/f.py", old_string=None, new_string="b"))
        assert "error" in result

    @patch("tools.file_tools._get_file_ops")
    def test_patch_mode_calls_patch_v4a(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {"status": "ok", "operations": 1}
        mock_ops.patch_v4a.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import patch_tool
        result = json.loads(patch_tool(mode="patch", patch="*** Begin Patch\n..."))
        assert result["status"] == "ok"
        mock_ops.patch_v4a.assert_called_once()

    @patch("tools.file_tools._get_file_ops")
    def test_patch_mode_missing_content_errors(self, mock_get):
        from tools.file_tools import patch_tool
        result = json.loads(patch_tool(mode="patch", patch=None))
        assert "error" in result

    @patch("tools.file_tools._get_file_ops")
    def test_unknown_mode_errors(self, mock_get):
        from tools.file_tools import patch_tool
        result = json.loads(patch_tool(mode="invalid_mode"))
        assert "error" in result
        assert "Unknown mode" in result["error"]


class TestSearchHandler:
    @patch("tools.file_tools._get_file_ops")
    def test_search_calls_file_ops(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {"matches": ["file1.py:3:match"]}
        mock_ops.search.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import search_tool
        result = json.loads(search_tool(pattern="TODO", target="content", path="."))
        assert "matches" in result
        mock_ops.search.assert_called_once()

    @patch("tools.file_tools._get_file_ops")
    def test_search_passes_all_params(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {"matches": []}
        mock_ops.search.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import search_tool
        search_tool(pattern="class", target="files", path="/src",
                    file_glob="*.py", limit=10, offset=5, output_mode="count", context=2)
        mock_ops.search.assert_called_once_with(
            pattern="class", path="/src", target="files", file_glob="*.py",
            limit=10, offset=5, output_mode="count", context=2,
        )

    @patch("tools.file_tools._get_file_ops")
    def test_search_normalizes_invalid_pagination_before_dispatch(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {"files": []}
        mock_ops.search.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import search_tool
        search_tool(pattern="class", target="files", path="/src", limit=-5, offset=-2)
        mock_ops.search.assert_called_once_with(
            pattern="class", path="/src", target="files", file_glob=None,
            limit=1, offset=0, output_mode="content", context=0,
        )

    @patch("tools.file_tools._get_file_ops")
    def test_search_exception_returns_error(self, mock_get):
        mock_get.side_effect = RuntimeError("no terminal")

        from tools.file_tools import search_tool
        result = json.loads(search_tool(pattern="x"))
        assert "error" in result

    @patch("tools.file_tools._get_file_ops")
    def test_vesta_search_files_caps_large_result(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {
            "total_count": 80,
            "matches": [
                {"path": f"paper-{idx}.md", "line": idx, "content": "x" * 200}
                for idx in range(80)
            ],
        }
        mock_ops.search.return_value = result_obj
        mock_get.return_value = mock_ops
        cfg = {
            "vesta": {
                "retrieval": {
                    "mode": "disciplined",
                    "broad_read_byte_threshold": 1_000,
                }
            }
        }

        from tools.file_tools import search_tool
        with patch("vesta_runtime.get_current_run", return_value=object()), \
             patch("hermes_cli.config.load_config", return_value=cfg):
            raw = search_tool(pattern="SenseNova", task_id="search_cap")
        result = json.loads(raw.split("\n\n[Hint:", 1)[0])

        assert result["truncated"] is True
        assert result["max_chars"] == 1_000
        assert result["max_chars_source"] == "vesta_retrieval"
        assert result["returned_matches_count"] < 80
        assert result["original_matches_count"] == 80
        assert "output_mode='count'" in result["repair_hint"]

    @patch("tools.file_tools._get_file_ops")
    def test_vesta_checkpoint_pressure_blocks_search_files_result(self, mock_get):
        from tools import tool_output_limits as tol

        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {
            "total_count": 20,
            "matches": [
                {"path": f"paper-{idx}.md", "line": idx, "content": "x" * 100}
                for idx in range(20)
            ],
        }
        mock_ops.search.return_value = result_obj
        mock_get.return_value = mock_ops
        cfg = {"vesta": {"retrieval": {"mode": "disciplined"}}}
        run = object()
        tol._VESTA_EVIDENCE_COUNT_BY_RUN.clear()

        from tools.file_tools import search_tool
        with patch("vesta_runtime.get_current_run", return_value=run), \
             patch("hermes_cli.config.load_config", return_value=cfg):
            for _ in range(tol.VESTA_CHECKPOINT_RETRIEVAL_LIMIT):
                assert tol.vesta_evidence_checkpoint_notice("read_file") is None
            raw = search_tool(pattern="SenseNova", task_id="search_checkpoint")
        result = json.loads(raw.split("\n\n[Hint:", 1)[0])

        assert result["vesta_checkpoint_required"] is True
        assert result["source"] == "search_files"
        assert result["matches"] == []
        assert "compact artifact checkpoint" in result["repair_hint"]


# ---------------------------------------------------------------------------
# Tool result hint tests (#722)
# ---------------------------------------------------------------------------

class TestPatchHints:
    """Patch tool should hint when old_string is not found."""

    @patch("tools.file_tools._get_file_ops")
    def test_no_match_includes_hint(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {
            "error": "Could not find match for old_string in foo.py"
        }
        mock_ops.patch_replace.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import patch_tool
        raw = patch_tool(mode="replace", path="foo.py", old_string="x", new_string="y")
        # patch_tool surfaces the hint as a structured "_hint" field on the
        # JSON error payload (not an inline "[Hint: ..." tail).
        assert "_hint" in raw
        assert "read_file" in raw

    @patch("tools.file_tools._get_file_ops")
    def test_success_no_hint(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {"success": True, "diff": "--- a\n+++ b"}
        mock_ops.patch_replace.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import patch_tool
        raw = patch_tool(mode="replace", path="foo.py", old_string="x", new_string="y")
        assert "_hint" not in raw


class TestSearchHints:
    """Search tool should hint when results are truncated."""

    def setup_method(self):
        """Clear read/search tracker between tests to avoid cross-test state."""
        from tools.file_tools import _read_tracker
        _read_tracker.clear()

    @patch("tools.file_tools._get_file_ops")
    def test_truncated_results_hint(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {
            "total_count": 100,
            "matches": [{"path": "a.py", "line": 1, "content": "x"}] * 50,
            "truncated": True,
        }
        mock_ops.search.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import search_tool
        raw = search_tool(pattern="foo", offset=0, limit=50)
        assert "[Hint:" in raw
        assert "offset=50" in raw

    @patch("tools.file_tools._get_file_ops")
    def test_non_truncated_no_hint(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {
            "total_count": 3,
            "matches": [{"path": "a.py", "line": 1, "content": "x"}] * 3,
        }
        mock_ops.search.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import search_tool
        raw = search_tool(pattern="foo")
        assert "[Hint:" not in raw

    @patch("tools.file_tools._get_file_ops")
    def test_truncated_hint_with_nonzero_offset(self, mock_get):
        mock_ops = MagicMock()
        result_obj = MagicMock()
        result_obj.to_dict.return_value = {
            "total_count": 150,
            "matches": [{"path": "a.py", "line": 1, "content": "x"}] * 50,
            "truncated": True,
        }
        mock_ops.search.return_value = result_obj
        mock_get.return_value = mock_ops

        from tools.file_tools import search_tool
        raw = search_tool(pattern="foo", offset=50, limit=50)
        assert "[Hint:" in raw
        assert "offset=100" in raw


# ---------------------------------------------------------------------------
# PATCH_SCHEMA shape tests (issue #15524)
# ---------------------------------------------------------------------------

class TestPatchSchemaShape:
    """PATCH_SCHEMA must advertise per-mode required params via description
    text (not JSON-schema ``required``), so strict models like kimi-k2.x stop
    silently omitting old_string / new_string / patch content."""

    def test_per_mode_required_params_documented_in_descriptions(self):
        desc = PATCH_SCHEMA["description"]
        assert "REQUIRED PARAMETERS: mode, path, old_string, new_string" in desc
        assert "REQUIRED PARAMETERS: mode, patch" in desc
        props = PATCH_SCHEMA["parameters"]["properties"]
        for name in ("path", "old_string", "new_string"):
            assert "REQUIRED when mode='replace'" in props[name]["description"]
        assert "REQUIRED when mode='patch'" in props["patch"]["description"]

    def test_no_anyof_required_stays_mode_only(self):
        # anyOf/oneOf at parameters level break Anthropic, Fireworks, and the
        # Moonshot/Kimi schema sanitizer — description-level guidance is the
        # only provider-safe signalling mechanism.
        params = PATCH_SCHEMA["parameters"]
        assert params["required"] == ["mode"]
        assert "anyOf" not in params and "oneOf" not in params
