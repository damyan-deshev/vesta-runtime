import json
import os
from pathlib import Path

from model_tools import handle_function_call
from vesta_runtime import create_run, process_document, set_current_run


def _write_vesta_whole_doc_config(max_chunk_tokens: int = 20, token_threshold: int = 30) -> None:
    config_path = Path(os.environ["HERMES_HOME"]) / "config.yaml"
    config_path.write_text(
        "vesta:\n"
        "  whole_document:\n"
        f"    token_threshold: {token_threshold}\n"
        f"    max_chunk_tokens: {max_chunk_tokens}\n",
        encoding="utf-8",
    )


def test_process_document_chunks_and_carries_prior_recap(tmp_path):
    set_current_run(None)
    _write_vesta_whole_doc_config(max_chunk_tokens=18, token_threshold=20)
    run = create_run(session_id="session_doc", workspace_path=tmp_path, run_id="run_doc")
    doc = tmp_path / "paper.md"
    doc.write_text(
        "# Paper\n"
        "Definition: Alpha means the shared hidden variable.\n"
        "Methods: We measure Alpha across repeated local trials.\n"
        "Results: Later sections use Alpha to explain the observed behavior.\n"
        "Conclusion: Alpha remains the primary explanatory term.\n",
        encoding="utf-8",
    )

    result = process_document(
        path=str(doc),
        objective="Explain the paper.",
        session_id="session_doc",
    )

    assert result["chunk_count"] > 1
    assert result["chunks"][1]["prior_recap"]
    assert "Alpha" in result["chunks"][1]["prior_recap"]
    assert result["chunks"][0]["raw_ref"].startswith("raw/doc_")
    assert (run.run_dir / result["chunks"][0]["raw_ref"]).exists()
    ledger = run.ledger_path.read_text(encoding="utf-8")
    assert "Document chunk 1/" in ledger
    assert "Whole-document rolling recap" in ledger
    assert "Explain the paper." in ledger


def test_whole_document_read_tool_returns_manifest(tmp_path, monkeypatch):
    set_current_run(None)
    _write_vesta_whole_doc_config(max_chunk_tokens=18, token_threshold=20)
    run = create_run(session_id="session_doc_tool", workspace_path=tmp_path, run_id="run_doc_tool")
    monkeypatch.setenv("HERMES_SESSION_ID", "session_doc_tool")
    doc = tmp_path / "report.md"
    doc.write_text(
        "Intro defines Beta as the operating constraint.\n"
        "Body depends on Beta for interpretation.\n"
        "Conclusion returns to Beta.\n",
        encoding="utf-8",
    )

    raw = handle_function_call(
        "whole_document_read",
        {"path": str(doc), "objective": "Summarize all sections."},
        session_id="session_doc_tool",
    )

    result = json.loads(raw)
    assert result["success"] is True
    assert result["chunk_count"] >= 1
    assert result["chunks"][0]["raw_ref"].startswith("raw/doc_")
    assert "rolling_recap" in result
    assert "Whole-document rolling recap" in run.ledger_path.read_text(encoding="utf-8")
