import json
import os
from pathlib import Path

from tools.file_tools import read_file_tool, search_tool
from vesta_runtime import create_run, set_current_run
from vesta_runtime.retrieval import reset_locator_history


def _write_lines(path: Path, count: int) -> None:
    path.write_text("".join(f"line {i}\n" for i in range(1, count + 1)), encoding="utf-8")


def test_disciplined_mode_blocks_unjustified_broad_read(tmp_path):
    set_current_run(None)
    reset_locator_history()
    create_run(session_id="session_retrieval", workspace_path=tmp_path, run_id="run_retrieval")
    target = tmp_path / "large.txt"
    _write_lines(target, 300)

    result = json.loads(read_file_tool(str(target), offset=1, limit=500, task_id="task_block"))

    assert "Vesta retrieval policy blocked" in result["error"]
    assert result["vesta_retrieval_policy"]["mode"] == "disciplined"
    assert "Run search_files first to locate relevant sections." in result["vesta_retrieval_policy"]["repair"]


def test_disciplined_mode_allows_broad_read_after_locator(tmp_path):
    set_current_run(None)
    reset_locator_history()
    create_run(session_id="session_retrieval", workspace_path=tmp_path, run_id="run_retrieval_locator")
    target = tmp_path / "large.txt"
    _write_lines(target, 300)

    search_result = json.loads(search_tool("line 250", path=str(tmp_path), task_id="task_locator"))
    assert not search_result.get("error")

    result = json.loads(read_file_tool(str(target), offset=1, limit=500, task_id="task_locator"))

    assert "error" not in result
    assert result["_vesta_retrieval"]["broad"] is True


def test_disciplined_mode_allows_declared_complete_coverage(tmp_path):
    set_current_run(None)
    reset_locator_history()
    create_run(session_id="session_retrieval", workspace_path=tmp_path, run_id="run_retrieval_complete")
    target = tmp_path / "large.txt"
    _write_lines(target, 300)

    result = json.loads(
        read_file_tool(
            str(target),
            offset=1,
            limit=500,
            task_id="task_complete",
            complete_coverage=True,
        )
    )

    assert "error" not in result
    assert result["_vesta_retrieval"]["broad"] is True


def test_permissive_mode_allows_and_records_broad_read(tmp_path):
    set_current_run(None)
    reset_locator_history()
    config_path = Path(os.environ["HERMES_HOME"]) / "config.yaml"
    config_path.write_text(
        "vesta:\n"
        "  retrieval:\n"
        "    mode: permissive\n",
        encoding="utf-8",
    )
    run = create_run(session_id="session_retrieval", workspace_path=tmp_path, run_id="run_retrieval_permissive")
    target = tmp_path / "large.txt"
    _write_lines(target, 300)

    result = json.loads(read_file_tool(str(target), offset=1, limit=500, task_id="task_permissive"))

    assert "error" not in result
    assert result["_vesta_retrieval"]["mode"] == "permissive"
    ledger = run.ledger_path.read_text(encoding="utf-8")
    assert "Broad read allowed" in ledger
    assert "permissive broad read" in ledger
