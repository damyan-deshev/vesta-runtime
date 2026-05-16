import os
from pathlib import Path

from hermes_cli.config import DEFAULT_CONFIG, _KNOWN_ROOT_KEYS, load_config


def test_vesta_defaults_are_first_class_config():
    assert "vesta" in DEFAULT_CONFIG
    assert "vesta" in _KNOWN_ROOT_KEYS
    assert DEFAULT_CONFIG["vesta"]["retrieval"]["mode"] == "disciplined"
    assert DEFAULT_CONFIG["vesta"]["retrieval"]["broad_read_line_threshold"] == 200
    assert DEFAULT_CONFIG["vesta"]["retrieval"]["broad_read_byte_threshold"] == 20_000
    assert DEFAULT_CONFIG["vesta"]["retrieval"]["broad_read_token_threshold"] == 12_000
    assert DEFAULT_CONFIG["vesta"]["whole_document"]["token_threshold"] == 100_000
    assert DEFAULT_CONFIG["vesta"]["whole_document"]["max_chunk_tokens"] == 20_000
    assert DEFAULT_CONFIG["vesta"]["raw_retention"]["retain_by_default"] is True
    assert DEFAULT_CONFIG["vesta"]["raw_retention"]["purge_preserves_manifest"] is True
    assert DEFAULT_CONFIG["vesta"]["eval"]["enabled"] is False
    assert DEFAULT_CONFIG["vesta"]["eval"]["allow_background_review"] is False
    assert DEFAULT_CONFIG["vesta"]["eval"]["contract_profile"] == "artifact_positive"
    assert DEFAULT_CONFIG["vesta"]["eval"]["read_only_fixture_paths"] == []
    assert DEFAULT_CONFIG["vesta"]["eval"]["forbidden_write_paths"] == []
    assert DEFAULT_CONFIG["vesta"]["eval"]["forbidden_tool_args"] == []


def test_vesta_config_deep_merges_partial_user_override():
    config_path = Path(os.environ["HERMES_HOME"]) / "config.yaml"
    config_path.write_text(
        "vesta:\n"
        "  retrieval:\n"
        "    mode: permissive\n",
        encoding="utf-8",
    )

    cfg = load_config()

    assert cfg["vesta"]["retrieval"]["mode"] == "permissive"
    assert cfg["vesta"]["retrieval"]["broad_read_line_threshold"] == 200
    assert cfg["vesta"]["whole_document"]["token_threshold"] == 100_000
    assert cfg["vesta"]["raw_retention"]["retain_by_default"] is True
    assert cfg["vesta"]["eval"]["allow_background_review"] is False
    assert cfg["vesta"]["eval"]["contract_profile"] == "artifact_positive"
