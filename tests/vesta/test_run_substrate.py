from pathlib import Path

from run_agent import AIAgent
from vesta_runtime import create_run, get_current_run, record_artifact, record_session_rotation, set_current_run, write_finalization


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
        context_length=65_536,
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
    assert "Context Length Tokens: `65536`" in run_md
    assert run.context_length == 65_536
    assert get_current_run().context_length == 65_536
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


def test_agent_vesta_run_uses_smaller_custom_provider_context():
    set_current_run(None)

    agent = AIAgent(
        model="test/small-context",
        provider="test",
        api_key="test",
        base_url="http://localhost:9/v1",
        quiet_mode=True,
        skip_memory=True,
        enabled_toolsets=[],
    )
    agent.context_compressor.context_length = 196_608
    agent._custom_providers = [
        {
            "base_url": "http://localhost:9/v1",
            "models": {
                "test/small-context": {
                    "context_length": 65_536,
                },
            },
        }
    ]

    agent._ensure_vesta_run(task_id="task_small_context")
    run = agent.vesta_run

    assert run is not None
    assert run.context_length == 65_536
    run_md = run.run_md_path.read_text(encoding="utf-8")
    assert "Context Length Tokens: `65536`" in run_md


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


def test_new_run_records_recovery_lineage_from_prior_blocked_run(tmp_path):
    set_current_run(None)
    blocked = create_run(
        session_id="session_blocked",
        workspace_path=tmp_path,
        run_id="run_blocked",
    )
    record_artifact(
        path="missing.md",
        artifact_type="report",
        expected_by="user_request",
        status="expected",
        session_id="session_blocked",
    )
    write_finalization(
        objective="Produce missing report.",
        verification="Checked manifest.",
        session_id="session_blocked",
    )

    recovery = create_run(
        session_id="session_recovery",
        workspace_path=tmp_path,
        run_id="run_recovery",
    )

    run_md = recovery.run_md_path.read_text(encoding="utf-8")
    assert "Recovery Of Run ID: `run_blocked`" in run_md
    assert "Supersedes Run ID: `run_blocked`" in run_md
    assert "Resumed From Session ID: `session_blocked`" in run_md
    assert blocked.run_id == "run_blocked"
