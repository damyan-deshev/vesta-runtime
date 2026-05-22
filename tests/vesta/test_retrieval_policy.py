import json
import os
from pathlib import Path

from tools.file_tools import READ_FILE_SCHEMA, read_file_tool, search_tool
from vesta_runtime import create_run, set_current_run
from vesta_runtime.retrieval import build_retrieval_prompt_contract, reset_locator_history


def _write_lines(path: Path, count: int) -> None:
    path.write_text("".join(f"line {i}\n" for i in range(1, count + 1)), encoding="utf-8")


def test_retrieval_prompt_contract_includes_duplicate_and_proxy_guidance():
    contract = build_retrieval_prompt_contract()

    assert "Vesta retrieval discipline:" in contract
    assert "unchanged/BLOCKED" in contract
    assert "synthesize once evidence is adequate" in contract
    assert "do not bypass" in contract
    assert len(contract.splitlines()) <= 7


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


def test_disciplined_mode_default_read_limit_stays_below_broad_threshold(tmp_path):
    set_current_run(None)
    reset_locator_history()
    create_run(session_id="session_retrieval", workspace_path=tmp_path, run_id="run_retrieval_default")
    target = tmp_path / "large.txt"
    _write_lines(target, 300)

    result = json.loads(read_file_tool(str(target), task_id="task_default"))

    assert "error" not in result
    assert result["total_lines"] == 300
    assert result["truncated"] is True
    assert "showing 1-180 of 300 lines" in result["hint"]
    assert "_vesta_retrieval" not in result
    assert READ_FILE_SCHEMA["parameters"]["properties"]["limit"]["default"] == 180


def test_disciplined_mode_allows_broad_read_after_locator(tmp_path):
    set_current_run(None)
    reset_locator_history()
    run = create_run(session_id="session_retrieval", workspace_path=tmp_path, run_id="run_retrieval_locator")
    target = tmp_path / "large.txt"
    _write_lines(target, 300)

    search_result = json.loads(search_tool("line 250", path=str(tmp_path), task_id="task_locator"))
    assert not search_result.get("error")

    result = json.loads(read_file_tool(str(target), offset=1, limit=500, task_id="task_locator"))

    assert "error" not in result
    assert result["_vesta_retrieval"]["broad"] is True
    assert result["_vesta_retrieval"]["locator_present"] is True
    ledger = run.ledger_path.read_text(encoding="utf-8")
    assert "Broad read allowed" in ledger
    assert "relevant locator-first evidence present" in ledger


def test_disciplined_mode_blocks_broad_read_after_zero_result_locator(tmp_path):
    set_current_run(None)
    reset_locator_history()
    create_run(session_id="session_retrieval", workspace_path=tmp_path, run_id="run_retrieval_zero_locator")
    target = tmp_path / "large.txt"
    _write_lines(target, 300)

    search_result = json.loads(search_tool("no such text", path=str(tmp_path), task_id="task_zero_locator"))
    assert search_result["total_count"] == 0
    result = json.loads(read_file_tool(str(target), offset=1, limit=500, task_id="task_zero_locator"))

    assert "Vesta retrieval policy blocked" in result["error"]


def test_disciplined_mode_blocks_broad_read_after_unrelated_locator(tmp_path):
    set_current_run(None)
    reset_locator_history()
    create_run(session_id="session_retrieval", workspace_path=tmp_path, run_id="run_retrieval_unrelated_locator")
    target = tmp_path / "large.txt"
    unrelated = tmp_path / "unrelated.txt"
    _write_lines(target, 300)
    unrelated.write_text("needle\n", encoding="utf-8")

    search_result = json.loads(search_tool("needle", path=str(tmp_path), task_id="task_unrelated_locator"))
    assert search_result["total_count"] == 1
    result = json.loads(read_file_tool(str(target), offset=1, limit=500, task_id="task_unrelated_locator"))

    assert "Vesta retrieval policy blocked" in result["error"]


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
