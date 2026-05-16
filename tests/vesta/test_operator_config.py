import json
import os
from pathlib import Path

from model_tools import handle_function_call
from vesta_runtime import capture_raw_output, create_run, purge_raw_ref, set_current_run


def test_run_metadata_captures_effective_vesta_config(tmp_path):
    set_current_run(None)
    config_path = Path(os.environ["HERMES_HOME"]) / "config.yaml"
    config_path.write_text(
        "vesta:\n"
        "  retrieval:\n"
        "    mode: permissive\n"
        "  whole_document:\n"
        "    token_threshold: 50000\n",
        encoding="utf-8",
    )

    run = create_run(session_id="session_operator", workspace_path=tmp_path, run_id="run_operator")

    run_md = run.run_md_path.read_text(encoding="utf-8")
    assert "## Vesta Effective Config" in run_md
    assert "Retrieval Mode: `permissive`" in run_md
    assert "Broad Read Line Threshold: `200`" in run_md
    assert "Whole Document Token Threshold: `50000`" in run_md
    assert "Raw Retention Purge Preserves Manifest: `True`" in run_md
    assert "Runtime prompt/tool surface should remain stable within a run." in run_md


def test_raw_ref_purge_preserves_manifest_and_ledger(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_purge", workspace_path=tmp_path, run_id="run_purge")
    raw = capture_raw_output(
        content="payload",
        source="terminal",
        tool_use_id="tool_payload",
        session_id="session_purge",
    )

    result = purge_raw_ref(
        raw_ref=raw["raw_ref"],
        reason="Operator requested local raw retention cleanup.",
        session_id="session_purge",
    )

    assert result["status"] == "purged"
    assert not (run.run_dir / raw["raw_ref"]).exists()
    raw_index = run.raw_index_path.read_text(encoding="utf-8")
    ledger = run.ledger_path.read_text(encoding="utf-8")
    assert raw["raw_ref"] in raw_index
    assert "Status: `purged`" in raw_index
    assert "Operator requested local raw retention cleanup." in raw_index
    assert f"Raw ref `{raw['raw_ref']}` is `purged`" in ledger


def test_raw_ref_purge_tool_marks_missing_refs(tmp_path, monkeypatch):
    set_current_run(None)
    run = create_run(session_id="session_purge_tool", workspace_path=tmp_path, run_id="run_purge_tool")
    monkeypatch.setenv("HERMES_SESSION_ID", "session_purge_tool")

    raw = handle_function_call(
        "raw_ref_purge",
        {
            "raw_ref": "raw/missing.txt",
            "reason": "Payload already absent.",
        },
        session_id="session_purge_tool",
    )
    result = json.loads(raw)

    assert result["success"] is True
    assert result["status"] == "missing"
    raw_index = run.raw_index_path.read_text(encoding="utf-8")
    assert "raw/missing.txt" in raw_index
    assert "Status: `missing`" in raw_index
