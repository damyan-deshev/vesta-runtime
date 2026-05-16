import json

from tools.file_tools import patch_tool, write_file_tool
from vesta_runtime import create_run, set_current_run


def test_eval_fixture_policy_blocks_write_file_to_read_only_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    monkeypatch.setenv("VESTA_EVAL_READ_ONLY_PATHS", str(fixture))
    set_current_run(None)
    create_run(session_id="session_fixture", workspace_path=tmp_path, run_id="run_fixture")

    result = json.loads(write_file_tool(str(fixture / "target.py"), "VALUE = 2\n", task_id="fixture_task"))

    assert "Vesta eval fixture policy blocked" in result["error"]
    assert not (fixture / "target.py").exists()


def test_eval_fixture_policy_blocks_patch_to_forbidden_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    fixture = tmp_path / "fixture.py"
    fixture.write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setenv("VESTA_EVAL_FORBIDDEN_WRITE_PATHS", str(fixture))
    set_current_run(None)
    create_run(session_id="session_fixture_patch", workspace_path=tmp_path, run_id="run_fixture_patch")

    result = json.loads(
        patch_tool(
            mode="replace",
            path=str(fixture),
            old_string="VALUE = 1",
            new_string="VALUE = 2",
            task_id="fixture_task",
        )
    )

    assert "Vesta eval fixture policy blocked" in result["error"]
    assert fixture.read_text(encoding="utf-8") == "VALUE = 1\n"
