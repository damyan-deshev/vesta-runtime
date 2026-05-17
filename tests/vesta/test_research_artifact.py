import json
from unittest.mock import patch

from model_tools import handle_function_call
from vesta_runtime import (
    create_run,
    run_status,
    set_current_run,
    write_control_plane_snapshot,
    write_research_artifact_section,
)


def test_research_artifact_sections_build_report_and_manifest_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_ID", "session_research_artifact")
    set_current_run(None)
    run = create_run(
        session_id="session_research_artifact",
        workspace_path=tmp_path,
        run_id="run_research_artifact",
    )
    report = "live-eval-artifacts/sensenova.md"

    write_research_artifact_section(
        path=report,
        section="sources",
        content="- HF model card: https://huggingface.co/sensenova/SenseNova-U1-8B-MoT",
        session_id="session_research_artifact",
    )
    result = write_research_artifact_section(
        path=report,
        section="claims_verdict",
        content="- Verdict: not accepted as groundbreaking without stronger paper/community evidence.",
        session_id="session_research_artifact",
    )

    artifact_path = tmp_path / report
    assert result["artifact_status"] == "exists"
    assert result["artifact_verified"] is True
    assert artifact_path.exists()
    text = artifact_path.read_text(encoding="utf-8")
    assert "## Sources" in text
    assert "## Claims / Verdict" in text

    manifest = run.artifact_manifest_path.read_text(encoding="utf-8")
    assert "Type: `research_artifact`" in manifest
    assert "Expected By: `research_artifact_section_write`" in manifest
    assert "Status: `exists`" in manifest

    status = run_status(session_id="session_research_artifact")
    artifacts = status["artifacts"]["artifacts"]
    assert any(
        artifact.get("path") == report and artifact.get("status") == "exists"
        for artifact in artifacts
    )

    write_control_plane_snapshot(
        session_id="session_research_artifact",
        next_action="Review research artifact.",
    )
    control_plane = run.control_plane_path.read_text(encoding="utf-8")
    assert "## Artifact Summary" in control_plane
    assert report in control_plane


def test_research_artifact_section_tool_rejects_oversized_section(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_ID", "session_research_artifact_tool")
    set_current_run(None)
    create_run(
        session_id="session_research_artifact_tool",
        workspace_path=tmp_path,
        run_id="run_research_artifact_tool",
    )
    cfg = {
        "vesta": {
            "retrieval": {
                "mode": "disciplined",
                "broad_read_byte_threshold": 8,
            }
        }
    }

    with patch("hermes_cli.config.load_config", return_value=cfg):
        raw = handle_function_call(
            "research_artifact_section_write",
            {
                "path": "live-eval-artifacts/report.md",
                "section": "sources",
                "content": "x" * 20,
            },
            session_id="session_research_artifact_tool",
        )

    result = json.loads(raw)
    assert result["success"] is False
    assert "too large" in result["error"]
    assert not (tmp_path / "live-eval-artifacts" / "report.md").exists()


def test_research_artifact_section_tool_missing_args_returns_repair_hint():
    raw = handle_function_call("research_artifact_section_write", {}, session_id="session_missing_args")

    result = json.loads(raw)
    assert result["success"] is False
    assert result["code"] == "vesta_research_artifact_section_args_missing_or_corrupt"
    assert "write_file" in result["repair_hint"]
    assert "sources" in result["repair_hint"]
