from pathlib import Path

from run_agent import AIAgent
from vesta_runtime import create_run, get_current_run, record_session_rotation, set_current_run


def test_create_run_seeds_markdown_files_under_hermes_home(monkeypatch, tmp_path):
    set_current_run(None)
    workspace = tmp_path / "project"
    workspace.mkdir()

    run = create_run(
        session_id="session_a",
        parent_session_id="parent_a",
        task_id="task_a",
        workspace_path=workspace,
        model="model-a",
        provider="provider-a",
        platform="cli",
        run_id="run_test_seed",
    )

    assert run.run_id == "run_test_seed"
    assert run.run_dir.exists()
    assert run.run_md_path.exists()
    assert run.ledger_path.exists()
    assert run.raw_index_path.exists()
    assert "vesta/workspaces" in str(run.run_dir)
    assert str(run.run_dir).startswith(str(Path.cwd())) is False

    run_md = run.run_md_path.read_text(encoding="utf-8")
    ledger = run.ledger_path.read_text(encoding="utf-8")
    assert "Run ID: `run_test_seed`" in run_md
    assert "Hermes Session ID: `session_a`" in run_md
    assert "Hermes Parent Session ID: `parent_a`" in run_md
    assert "# Vesta Ledger" in ledger
    assert "## Entries" in ledger
    assert get_current_run() == run


def test_agent_initializes_vesta_run_at_session_start():
    set_current_run(None)

    agent = AIAgent(
        model="test/model",
        provider="test",
        api_key="test",
        base_url="http://localhost:9/v1",
        quiet_mode=True,
        skip_memory=True,
        enabled_toolsets=[],
    )
    assert agent.vesta_run is None

    agent._ensure_vesta_run(task_id="task_start")
    run = agent.vesta_run
    assert run is not None
    assert run.run_md_path.exists()
    assert run.ledger_path.exists()
    run_md = run.run_md_path.read_text(encoding="utf-8")
    assert f"Hermes Session ID: `{agent.session_id}`" in run_md
    assert "Task ID: `task_start`" in run_md
    assert run.run_id != agent.session_id


def test_record_session_rotation_updates_run_and_ledger(tmp_path):
    set_current_run(None)
    run = create_run(
        session_id="session_old",
        workspace_path=tmp_path,
        run_id="run_rotation",
    )

    record_session_rotation(
        old_session_id="session_old",
        new_session_id="session_new",
        reason="compression",
    )

    run_md = run.run_md_path.read_text(encoding="utf-8")
    ledger = run.ledger_path.read_text(encoding="utf-8")
    assert "Old Session ID: `session_old`" in run_md
    assert "New Session ID: `session_new`" in run_md
    assert "Hermes session rotated" in ledger
    assert "compression" in ledger
