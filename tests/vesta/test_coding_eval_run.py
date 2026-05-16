import json
from pathlib import Path

from model_tools import handle_function_call
from vesta_runtime import (
    capture_coding_eval_result,
    create_run,
    set_current_run,
    start_coding_eval,
)


def _seed_project(path: Path) -> None:
    path.mkdir()
    (path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (path / ".env").write_text("API_KEY=sk-secret123456\n", encoding="utf-8")
    (path / ".venv").mkdir()
    (path / ".venv" / "marker").write_text("venv", encoding="utf-8")


def test_coding_eval_starts_isolated_copy_with_exclusions_and_redaction(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_eval", workspace_path=tmp_path, run_id="run_eval")
    original = tmp_path / "original"
    _seed_project(original)

    eval_state = start_coding_eval(
        original_workspace=str(original),
        prompt="Change VALUE. token=sk-secret123456",
        model="qwen",
        provider="local",
        config={"api_key": "sk-secret123456", "temperature": 0},
        session_id="session_eval",
    )

    eval_workspace = Path(eval_state["eval_workspace"])
    assert eval_workspace.exists()
    assert (eval_workspace / "app.py").exists()
    assert not (eval_workspace / ".env").exists()
    assert not (eval_workspace / ".venv").exists()
    assert (original / "app.py").read_text(encoding="utf-8") == "VALUE = 1\n"

    eval_md = Path(eval_state["eval_md_path"]).read_text(encoding="utf-8")
    raw_index = run.raw_index_path.read_text(encoding="utf-8")
    assert "Excluded Paths:" in eval_md
    assert "raw/" in eval_md
    assert "coding_eval_prompt" in raw_index
    assert "coding_eval_config" in raw_index
    assert "sk-secret123456" not in raw_index
    assert "sk-secret123456" not in (run.raw_dir / f"{eval_state['eval_id']}_prompt.txt").read_text(encoding="utf-8")


def test_coding_eval_capture_records_diff_and_verification_refs(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_eval_capture", workspace_path=tmp_path, run_id="run_eval_capture")
    original = tmp_path / "original"
    _seed_project(original)
    eval_state = start_coding_eval(
        original_workspace=str(original),
        prompt="Change VALUE.",
        session_id="session_eval_capture",
    )
    eval_workspace = Path(eval_state["eval_workspace"])
    (eval_workspace / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    result = capture_coding_eval_result(
        eval_id=eval_state["eval_id"],
        verification_command="pytest -q",
        verification_exit_status=0,
        verification_output="1 passed\n",
        session_id="session_eval_capture",
    )

    assert result["verdict"] == "accepted"
    diff = (run.raw_dir / f"{eval_state['eval_id']}_diff.txt").read_text(encoding="utf-8")
    verification = (run.raw_dir / f"{eval_state['eval_id']}_verification.txt").read_text(encoding="utf-8")
    eval_md = Path(eval_state["eval_md_path"]).read_text(encoding="utf-8")
    assert "-VALUE = 1" in diff
    assert "+VALUE = 2" in diff
    assert "1 passed" in verification
    assert "Final Verdict: `accepted`" in eval_md
    assert (original / "app.py").read_text(encoding="utf-8") == "VALUE = 1\n"


def test_failed_coding_eval_without_reason_is_blocked(tmp_path):
    set_current_run(None)
    create_run(session_id="session_eval_failed", workspace_path=tmp_path, run_id="run_eval_failed")
    original = tmp_path / "original"
    _seed_project(original)
    eval_state = start_coding_eval(
        original_workspace=str(original),
        prompt="Break VALUE.",
        session_id="session_eval_failed",
    )

    result = capture_coding_eval_result(
        eval_id=eval_state["eval_id"],
        verification_command="pytest -q",
        verification_exit_status=1,
        verification_output="failed\n",
        session_id="session_eval_failed",
    )

    assert result["verdict"] == "blocked"
    assert result["blockers"] == ["failed_verification_without_reason"]


def test_coding_eval_tools_update_active_run(tmp_path, monkeypatch):
    set_current_run(None)
    create_run(session_id="session_eval_tool", workspace_path=tmp_path, run_id="run_eval_tool")
    monkeypatch.setenv("HERMES_SESSION_ID", "session_eval_tool")
    original = tmp_path / "original"
    _seed_project(original)

    start_raw = handle_function_call(
        "coding_eval_start",
        {
            "original_workspace": str(original),
            "prompt": "Update VALUE.",
            "model": "qwen",
            "provider": "local",
        },
        session_id="session_eval_tool",
    )
    start_result = json.loads(start_raw)
    assert start_result["success"] is True

    eval_workspace = Path(start_result["eval_workspace"])
    (eval_workspace / "app.py").write_text("VALUE = 3\n", encoding="utf-8")
    capture_raw = handle_function_call(
        "coding_eval_capture",
        {
            "eval_id": start_result["eval_id"],
            "verification_command": "pytest -q",
            "verification_exit_status": 0,
            "verification_output": "1 passed\n",
        },
        session_id="session_eval_tool",
    )
    capture_result = json.loads(capture_raw)
    assert capture_result["success"] is True
    assert capture_result["verdict"] == "accepted"
