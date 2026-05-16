from tools.budget_config import BudgetConfig
from tools.tool_result_storage import PERSISTED_OUTPUT_TAG, maybe_persist_tool_result
from vesta_runtime import capture_raw_output, create_run, set_current_run


def test_capture_raw_output_writes_payload_and_index(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_raw", workspace_path=tmp_path, run_id="run_raw")

    raw = capture_raw_output(
        content="alpha\nbeta\ngamma\n",
        source="terminal",
        tool_use_id="tool_1",
        session_id="session_raw",
    )

    assert raw["raw_ref"] == "raw/tool_1.txt"
    assert raw["hash"].startswith("sha256:")
    assert (run.run_dir / raw["raw_ref"]).read_text(encoding="utf-8") == "alpha\nbeta\ngamma\n"
    index = run.raw_index_path.read_text(encoding="utf-8")
    assert "raw/tool_1.txt" in index
    assert "terminal" in index


def test_tool_result_persistence_prefers_active_vesta_run(tmp_path, monkeypatch):
    set_current_run(None)
    run = create_run(session_id="session_persist", workspace_path=tmp_path, run_id="run_persist")
    monkeypatch.setenv("HERMES_SESSION_ID", "session_persist")

    content = "x" * 50
    result = maybe_persist_tool_result(
        content=content,
        tool_name="terminal",
        tool_use_id="tool_big",
        env=None,
        config=BudgetConfig(default_result_size=10, preview_size=8),
        threshold=10,
    )

    assert PERSISTED_OUTPUT_TAG in result
    assert "Vesta raw ref: raw/tool_big.txt" in result
    assert (run.raw_dir / "tool_big.txt").read_text(encoding="utf-8") == content
    assert "raw/tool_big.txt" in run.raw_index_path.read_text(encoding="utf-8")
