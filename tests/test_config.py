"""Tests for config loading and validation."""

import pytest
import yaml

from pandemonium.tgbot.config import AppConfig, ConfigError, load_config


def _write_yaml(tmp_path, data: dict) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(data))


def _valid_config(tmp_path) -> dict:
    """Return a minimal valid config dict (project path must exist)."""
    return {
        "telegram": {"bot_token": "test-token"},
        "allowed_users": [{"telegram_id": 111, "name": "Alice"}],
        "projects": [
            {"id": "proj", "name": "Test Project", "path": str(tmp_path)}
        ],
    }


def test_load_valid_config(tmp_path):
    data = _valid_config(tmp_path)
    _write_yaml(tmp_path, data)
    cfg = load_config(tmp_path / "config.yaml")

    assert isinstance(cfg, AppConfig)
    assert cfg.telegram.bot_token == "test-token"
    assert cfg.allowed_user_ids == {111}
    assert cfg.default_project.id == "pandemonium-bot"  # bot project is always first
    assert any(p.id == "proj" for p in cfg.projects)
    assert cfg.storage.base_path.is_absolute()
    assert cfg.token_budget.per_request_limit == 0


def test_load_config_with_all_fields(tmp_path):
    data = _valid_config(tmp_path)
    data["storage"] = {"base_path": str(tmp_path / "sessions")}
    data["token_budget"] = {"per_request_limit": 50000}
    _write_yaml(tmp_path, data)

    cfg = load_config(tmp_path / "config.yaml")
    assert cfg.token_budget.per_request_limit == 50000


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nonexistent.yaml")


def test_invalid_yaml(tmp_path):
    (tmp_path / "bad.yaml").write_text("{unclosed: [bracket")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(tmp_path / "bad.yaml")


def test_missing_required_field(tmp_path):
    _write_yaml(tmp_path, {"telegram": {"bot_token": "t"}})
    with pytest.raises(ConfigError, match="validation error"):
        load_config(tmp_path / "config.yaml")


def test_invalid_project_path(tmp_path):
    data = _valid_config(tmp_path)
    data["projects"][0]["path"] = "/nonexistent/path/12345"
    _write_yaml(tmp_path, data)
    with pytest.raises(ConfigError, match="validation error"):
        load_config(tmp_path / "config.yaml")


def test_get_user_name(tmp_path):
    data = _valid_config(tmp_path)
    _write_yaml(tmp_path, data)
    cfg = load_config(tmp_path / "config.yaml")

    assert cfg.get_user_name(111) == "Alice"
    assert cfg.get_user_name(999) is None


def test_not_a_mapping(tmp_path):
    (tmp_path / "config.yaml").write_text("- list\n- items\n")
    with pytest.raises(ConfigError, match="must be a YAML mapping"):
        load_config(tmp_path / "config.yaml")
