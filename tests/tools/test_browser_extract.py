"""Tests for browser_extract rendered-page normalization."""

import json
import os
import sys
from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestBrowserExtract:
    def test_returns_normalized_markdown_shape(self):
        from tools.browser_tool import browser_extract

        eval_payload = {
            "success": True,
            "result": {
                "url": "https://example.com/app",
                "title": "Example App",
                "selector": "main",
                "html": "<main><h1>Example</h1><script>bad()</script><p>Hello world</p></main>",
                "text": "Example\nHello world",
                "html_chars": 72,
                "text_chars": 19,
                "html_truncated": False,
                "text_truncated": False,
            },
        }

        with (
            patch("tools.browser_tool._browser_eval", return_value=json.dumps(eval_payload)) as mock_eval,
            patch("tools.browser_tool._normalize_rendered_html", return_value=("# Example\n\nHello world", "trafilatura", None)),
        ):
            result = json.loads(browser_extract(selector="main", max_chars=12000, task_id="task"))

        assert result["success"] is True
        assert result["source"] == "browser_rendered"
        assert result["content_format"] == "normalized_markdown"
        assert "not raw HTML" in result["content_note"]
        assert result["normalizer"] == "trafilatura"
        assert result["content"] == "# Example\n\nHello world"
        assert result["url"] == "https://example.com/app"
        assert result["selector"] == "main"
        assert result["raw_input_truncated"] is False
        expression = mock_eval.call_args[0][0]
        assert "document.querySelector" in expression
        assert "main" in expression

    def test_truncates_content_on_line_boundary(self):
        from tools.browser_tool import browser_extract

        eval_payload = {
            "success": True,
            "result": {
                "url": "https://example.com/long",
                "title": "Long",
                "html": "<article>Long</article>",
                "text": "Long",
                "html_chars": 22,
                "text_chars": 4,
            },
        }
        content = "Intro\n" + ("x" * 1500) + "\nTail"

        with (
            patch("tools.browser_tool._browser_eval", return_value=json.dumps(eval_payload)),
            patch("tools.browser_tool._normalize_rendered_html", return_value=(content, "trafilatura", None)),
        ):
            result = json.loads(browser_extract(max_chars=1000, task_id="task"))

        assert result["success"] is True
        assert result["max_chars"] == 1000
        assert result["chars"] <= 1000
        assert result["omitted_chars"] > 0
        assert result["truncated"] is True
        assert "repair_hint" in result
        assert result["full_chars"] == len(content)

    def test_vesta_disciplined_run_caps_requested_max_chars(self):
        from tools.browser_tool import browser_extract

        eval_payload = {
            "success": True,
            "result": {
                "url": "https://example.com/long",
                "title": "Long",
                "html": "<article>Long</article>",
                "text": "Long",
                "html_chars": 22,
                "text_chars": 4,
            },
        }
        content = "Intro\n" + ("x" * 20_000) + "\nTail"

        with (
            patch("tools.browser_tool._browser_eval", return_value=json.dumps(eval_payload)),
            patch("tools.browser_tool._normalize_rendered_html", return_value=(content, "trafilatura", None)),
            patch("vesta_runtime.get_current_run", return_value=object()),
            patch(
                "hermes_cli.config.load_config",
                return_value={
                    "vesta": {
                        "retrieval": {
                            "mode": "disciplined",
                            "broad_read_byte_threshold": 12_000,
                        }
                    }
                },
            ),
        ):
            result = json.loads(browser_extract(max_chars=50_000, task_id="task"))

        assert result["success"] is True
        assert result["max_chars"] == 12_000
        assert result["max_chars_source"] == "vesta_retrieval"
        assert result["chars"] <= 12_000
        assert result["truncated"] is True
        assert result["omitted_chars"] > 0
        assert "bounded normalized markdown excerpt" in result["repair_hint"]

    def test_vesta_disciplined_run_tightens_browser_extract_for_small_context(self, monkeypatch):
        from tools.browser_tool import browser_extract

        eval_payload = {
            "success": True,
            "result": {
                "url": "https://example.com/context",
                "title": "Context",
                "html": "<article>Context</article>",
                "text": "Context",
                "html_chars": 26,
                "text_chars": 7,
            },
        }
        content = "Intro\n" + ("x" * 20_000) + "\nTail"
        monkeypatch.setenv("VESTA_CONTEXT_LENGTH_TOKENS", "65536")

        with (
            patch("tools.browser_tool._browser_eval", return_value=json.dumps(eval_payload)),
            patch("tools.browser_tool._normalize_rendered_html", return_value=(content, "trafilatura", None)),
            patch("vesta_runtime.get_current_run", return_value=object()),
            patch(
                "hermes_cli.config.load_config",
                return_value={
                    "vesta": {
                        "retrieval": {
                            "mode": "disciplined",
                            "broad_read_byte_threshold": 20_000,
                        }
                    }
                },
            ),
        ):
            result = json.loads(browser_extract(max_chars=50_000, task_id="context-test"))

        assert result["success"] is True
        assert result["max_chars"] == 8192
        assert result["max_chars_source"] == "vesta_context_retrieval"
        assert result["context_length_tokens"] == 65536
        assert result["chars"] <= 8192

    def test_vesta_checkpoint_pressure_blocks_browser_extract_content(self):
        from tools import tool_output_limits as tol
        from tools.browser_tool import browser_extract

        eval_payload = {
            "success": True,
            "result": {
                "url": "https://example.com/checkpoint-pressure",
                "title": "Checkpoint Pressure",
                "html": "<article>Small evidence</article>",
                "text": "Small evidence",
                "html_chars": 34,
                "text_chars": 14,
            },
        }
        run = object()
        cfg = {"vesta": {"retrieval": {"mode": "disciplined"}}}
        tol._VESTA_EVIDENCE_COUNT_BY_RUN.clear()

        with (
            patch("tools.browser_tool._browser_eval", return_value=json.dumps(eval_payload)),
            patch("tools.browser_tool._normalize_rendered_html", return_value=("Small evidence", "trafilatura", None)),
            patch("vesta_runtime.get_current_run", return_value=run),
            patch("hermes_cli.config.load_config", return_value=cfg),
        ):
            for _ in range(tol.VESTA_CHECKPOINT_RETRIEVAL_LIMIT):
                assert tol.vesta_evidence_checkpoint_notice("terminal") is None
            result = json.loads(browser_extract(task_id="checkpoint-pressure-test"))

        assert result["success"] is True
        assert result["vesta_checkpoint_required"] is True
        assert result["source"] == "browser_extract"
        assert result["content"] == ""
        assert result["chars"] == 0
        assert "compact artifact checkpoint" in result["repair_hint"]

    def test_vesta_caps_browser_navigate_snapshot_payload(self, monkeypatch):
        from tools.browser_tool import _apply_browser_snapshot_budget

        monkeypatch.setenv("VESTA_CONTEXT_LENGTH_TOKENS", "65536")
        response = {"success": True, "snapshot": "x" * 20_000}

        with (
            patch("vesta_runtime.get_current_run", return_value=object()),
            patch(
                "hermes_cli.config.load_config",
                return_value={
                    "vesta": {
                        "retrieval": {
                            "mode": "disciplined",
                            "broad_read_byte_threshold": 20_000,
                        }
                    }
                },
            ),
        ):
            result = _apply_browser_snapshot_budget(response, "browser_navigate")

        assert result["truncated"] is True
        assert result["max_chars"] == 8192
        assert result["max_chars_source"] == "vesta_context_retrieval"
        assert result["context_length_tokens"] == 65536
        assert len(result["snapshot"]) <= 8192
        assert "bounded page snapshot" in result["repair_hint"]

    def test_vesta_checkpoint_pressure_blocks_browser_snapshot_payload(self):
        from tools import tool_output_limits as tol
        from tools.browser_tool import _apply_browser_snapshot_budget

        response = {"success": True, "snapshot": "x" * 2_000}
        cfg = {"vesta": {"retrieval": {"mode": "disciplined"}}}
        run = object()
        tol._VESTA_EVIDENCE_COUNT_BY_RUN.clear()

        with (
            patch("vesta_runtime.get_current_run", return_value=run),
            patch("hermes_cli.config.load_config", return_value=cfg),
        ):
            for _ in range(tol.VESTA_CHECKPOINT_RETRIEVAL_LIMIT):
                assert tol.vesta_evidence_checkpoint_notice("read_file") is None
            result = _apply_browser_snapshot_budget(response, "browser_snapshot")

        assert result["vesta_checkpoint_required"] is True
        assert result["source"] == "browser_snapshot"
        assert result["snapshot"] == ""
        assert "compact artifact checkpoint" in result["repair_hint"]

    def test_vesta_duplicate_extract_returns_compact_notice(self):
        from tools.browser_tool import browser_extract

        eval_payload = {
            "success": True,
            "result": {
                "url": "https://example.com/repeated",
                "title": "Repeated",
                "html": "<main><p>Same evidence</p></main>",
                "text": "Same evidence",
                "html_chars": 32,
                "text_chars": 13,
            },
        }

        with (
            patch("tools.browser_tool._browser_eval", return_value=json.dumps(eval_payload)),
            patch("tools.browser_tool._normalize_rendered_html", return_value=("Same evidence", "trafilatura", None)),
            patch("vesta_runtime.get_current_run", return_value=object()),
            patch(
                "hermes_cli.config.load_config",
                return_value={
                    "vesta": {
                        "retrieval": {
                            "mode": "disciplined",
                            "broad_read_byte_threshold": 12_000,
                        }
                    }
                },
            ),
        ):
            first = json.loads(browser_extract(task_id="duplicate-test"))
            second = json.loads(browser_extract(task_id="duplicate-test"))

        assert first["success"] is True
        assert first.get("duplicate") is None
        assert first["content"] == "Same evidence"
        assert second["success"] is True
        assert second["duplicate"] is True
        assert second["content"] == ""
        assert second["chars"] == 0
        assert "same normalized content already returned" in second["repair_hint"]

    def test_vesta_repeat_page_extract_returns_compact_notice(self):
        from tools.browser_tool import browser_extract

        eval_payload = {
            "success": True,
            "result": {
                "url": "https://example.com/repeat-budget",
                "title": "Repeat Budget",
                "html": "<main><p>Evidence</p></main>",
                "text": "Evidence",
                "html_chars": 28,
                "text_chars": 8,
            },
        }
        normalized = [
            ("Evidence one", "trafilatura", None),
            ("Evidence two", "trafilatura", None),
            ("Evidence three", "trafilatura", None),
            ("Evidence four", "trafilatura", None),
        ]

        with (
            patch("tools.browser_tool._browser_eval", return_value=json.dumps(eval_payload)),
            patch("tools.browser_tool._normalize_rendered_html", side_effect=normalized),
            patch("vesta_runtime.get_current_run", return_value=object()),
            patch(
                "hermes_cli.config.load_config",
                return_value={
                    "vesta": {
                        "retrieval": {
                            "mode": "disciplined",
                            "broad_read_byte_threshold": 12_000,
                        }
                    }
                },
            ),
        ):
            first = json.loads(browser_extract(task_id="repeat-budget-test"))
            second = json.loads(browser_extract(task_id="repeat-budget-test"))
            third = json.loads(browser_extract(task_id="repeat-budget-test"))
            fourth = json.loads(browser_extract(task_id="repeat-budget-test"))

        assert first["content"] == "Evidence one"
        assert second["content"] == "Evidence two"
        assert third["content"] == "Evidence three"
        assert fourth["repeat_extract_limit_exceeded"] is True
        assert fourth["content"] == ""
        assert fourth["page_extract_count"] == 4
        assert "already extracted this rendered page several times" in fourth["repair_hint"]

    def test_vesta_browser_console_output_is_context_bounded(self, monkeypatch):
        from tools.browser_tool import browser_console

        monkeypatch.setenv("VESTA_CONTEXT_LENGTH_TOKENS", "65536")

        def fake_run_browser_command(_task_id, command, _args, **_kwargs):
            if command == "console":
                return {
                    "success": True,
                    "data": {
                        "messages": [
                            {
                                "type": "log",
                                "text": "x" * 20_000,
                            }
                        ]
                    },
                }
            if command == "errors":
                return {"success": True, "data": {"errors": []}}
            raise AssertionError(command)

        with (
            patch("tools.browser_tool._run_browser_command", side_effect=fake_run_browser_command),
            patch("tools.browser_tool._last_session_key", return_value="console-task"),
            patch("vesta_runtime.get_current_run", return_value=object()),
            patch(
                "hermes_cli.config.load_config",
                return_value={
                    "vesta": {
                        "retrieval": {
                            "mode": "disciplined",
                            "broad_read_byte_threshold": 20_000,
                        }
                    }
                },
            ),
        ):
            result = json.loads(browser_console(task_id="console-task"))

        assert result["success"] is True
        assert result["truncated"] is True
        assert result["max_chars"] == 8192
        assert result["max_chars_source"] == "vesta_context_retrieval"
        assert result["context_length_tokens"] == 65536
        assert result["console_messages"][0]["truncated"] is True
        assert len(result["console_messages"][0]["text"]) <= 8192
        assert "bounded text" in result["repair_hint"]

    def test_vesta_browser_console_expression_output_is_context_bounded(self, monkeypatch):
        from tools.browser_tool import browser_console

        monkeypatch.setenv("VESTA_CONTEXT_LENGTH_TOKENS", "65536")
        raw_eval = json.dumps({
            "success": True,
            "result": {"payload": "x" * 20_000},
            "result_type": "dict",
        })

        with (
            patch("tools.browser_tool._browser_eval", return_value=raw_eval),
            patch("vesta_runtime.get_current_run", return_value=object()),
            patch(
                "hermes_cli.config.load_config",
                return_value={
                    "vesta": {
                        "retrieval": {
                            "mode": "disciplined",
                            "broad_read_byte_threshold": 20_000,
                        }
                    }
                },
            ),
        ):
            result = json.loads(browser_console(expression="window.big", task_id="console-task"))

        assert result["success"] is True
        assert result["truncated"] is True
        assert result["result_truncated"] is True
        assert result["max_chars"] == 8192
        assert result["max_chars_source"] == "vesta_context_retrieval"
        assert result["context_length_tokens"] == 65536
        assert len(result["result"]) <= 8192
        assert "bounded JSON/text preview" in result["repair_hint"]

    def test_reports_selector_miss(self):
        from tools.browser_tool import browser_extract

        eval_payload = {
            "success": True,
            "result": {
                "error": "No element matched selector: article",
                "url": "https://example.com",
                "title": "Example",
                "selector": "article",
            },
        }

        with patch("tools.browser_tool._browser_eval", return_value=json.dumps(eval_payload)):
            result = json.loads(browser_extract(selector="article", task_id="task"))

        assert result["success"] is False
        assert "No element matched selector" in result["error"]
        assert result["selector"] == "article"

    def test_schema_and_registry_wiring(self):
        from model_tools import _LEGACY_TOOLSET_MAP
        from toolsets import TOOLSETS, _HERMES_CORE_TOOLS
        from tools import browser_tool  # noqa: F401
        from tools.browser_tool import BROWSER_TOOL_SCHEMAS
        from tools.registry import registry

        names = [schema["name"] for schema in BROWSER_TOOL_SCHEMAS]
        assert "browser_extract" in names
        assert "browser_extract" in TOOLSETS["browser"]["tools"]
        assert "browser_extract" in _HERMES_CORE_TOOLS
        assert "browser_extract" in _LEGACY_TOOLSET_MAP["browser_tools"]
        assert "browser_extract" in registry._tools
