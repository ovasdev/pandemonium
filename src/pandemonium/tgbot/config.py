"""Configuration loading and validation."""

import argparse
import logging
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

_BOT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CONFIG_PATH = _BOT_ROOT / "config.yaml"


class PandemoniumError(Exception):
    """Base exception for all Pandemonium Telegram bot errors."""


class ConfigError(PandemoniumError):
    """Configuration loading or validation error."""


class TelegramConfig(BaseModel):
    bot_token: str


class UserConfig(BaseModel):
    telegram_id: int
    name: str


class ProjectConfig(BaseModel):
    id: str
    name: str
    path: Path

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        expanded = v.expanduser().resolve()
        if not expanded.is_dir():
            raise ValueError(f"Project path does not exist: {expanded}")
        return expanded


class StorageConfig(BaseModel):
    base_path: Path = Path("~/.pandemonium/sessions")

    @field_validator("base_path")
    @classmethod
    def expand_base_path(cls, v: Path) -> Path:
        return v.expanduser().resolve()

    def model_post_init(self, __context: object) -> None:
        # Ensure expansion happens even for the default value
        object.__setattr__(
            self, "base_path", self.base_path.expanduser().resolve()
        )

    @property
    def uploads_path(self) -> Path:
        """Directory for files received from Telegram."""
        return self.base_path / "uploads"


class TokenBudgetConfig(BaseModel):
    per_request_limit: int = 0


class TimeoutsConfig(BaseModel):
    request_max_seconds: int = 1800  # 30 minutes


class AppConfig(BaseModel):
    telegram: TelegramConfig
    allowed_users: list[UserConfig]
    projects: list[ProjectConfig]
    storage: StorageConfig = StorageConfig()
    token_budget: TokenBudgetConfig = TokenBudgetConfig()
    timeouts: TimeoutsConfig = TimeoutsConfig()

    @property
    def allowed_user_ids(self) -> set[int]:
        return {u.telegram_id for u in self.allowed_users}

    @property
    def default_project(self) -> ProjectConfig:
        return self.projects[0]

    def get_user_name(self, telegram_id: int) -> str | None:
        for u in self.allowed_users:
            if u.telegram_id == telegram_id:
                return u.name
        return None

    def get_project(self, project_id: str) -> ProjectConfig | None:
        """Find a project by id."""
        for p in self.projects:
            if p.id == project_id:
                return p
        return None


def _ensure_bot_project(config: AppConfig) -> AppConfig:
    """Ensure the bot's own project is always projects[0] with the correct path."""
    for i, p in enumerate(config.projects):
        if p.path == _BOT_ROOT:
            if i == 0:
                return config
            # Move to front
            projects = [p] + config.projects[:i] + config.projects[i + 1:]
            return config.model_copy(update={"projects": projects})
    # Not found — add as first
    bot_project = ProjectConfig(
        id="pandemonium-bot", name="Pandemonium Bot", path=_BOT_ROOT,
    )
    return config.model_copy(
        update={"projects": [bot_project] + list(config.projects)},
    )


def load_config(path: Path) -> AppConfig:
    """Load and validate config from a YAML file."""
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError("Config must be a YAML mapping")

    try:
        config = AppConfig(**raw)
    except Exception as e:
        raise ConfigError(f"Config validation error: {e}") from e

    config = _ensure_bot_project(config)
    logger.info("Default project: %s (%s)", config.default_project.id, config.default_project.path)
    return config


def scan_personas(project_path: Path) -> list[str]:
    """Scan .agent/personas/ in a project directory.

    Returns a sorted list of persona names (directory names that contain PERSONA.md).
    """
    personas_dir = project_path / ".agent" / "personas"
    if not personas_dir.is_dir():
        return []
    names: list[str] = []
    for entry in personas_dir.iterdir():
        if entry.is_dir() and (entry / "PERSONA.md").is_file():
            names.append(entry.name)
    return sorted(names)


def resolve_config_path() -> Path:
    """Determine config path from CLI args, env var, or default."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", type=Path, default=None)
    args, _ = parser.parse_known_args()

    if args.config:
        return args.config

    env = os.environ.get("PANDEMONIUM_CONFIG")
    if env:
        return Path(env)

    return _DEFAULT_CONFIG_PATH
