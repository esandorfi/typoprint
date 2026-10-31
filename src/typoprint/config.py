"""Explicit project settings and named presets; no process-wide configuration."""

import tomllib
from pathlib import Path

from pydantic import Field, ValidationError

from typoprint.models import ConfigurationError, FrozenModel, Settings


class ProjectConfig(FrozenModel):
    defaults: Settings = Field(default_factory=Settings)
    presets: dict[str, Settings] = Field(default_factory=dict)


def _relative_paths(settings: Settings, directory: Path) -> Settings:
    data = settings.model_dump(exclude_unset=True)
    if settings.template not in ("editorial", "report"):
        data["template"] = str((directory / settings.template).resolve())
    if "font_paths" in data:
        data["font_paths"] = tuple(
            (directory / path).resolve() for path in settings.font_paths
        )
    return Settings.model_validate(data)


def load_settings(path: str | Path, *, preset: str | None = None) -> Settings:
    """Load defaults and one preset. Relative resources belong to the TOML file."""
    source = Path(path).resolve()
    try:
        config = ProjectConfig.model_validate(
            tomllib.loads(source.read_text(encoding="utf-8-sig"))
        )
    except (OSError, ValueError, ValidationError) as error:
        raise ConfigurationError(
            f"Cannot load settings from {source}: {error}"
        ) from error
    settings = _relative_paths(config.defaults, source.parent)
    if preset is not None:
        if preset not in config.presets:
            raise ConfigurationError(f"Unknown preset: {preset}")
        settings = settings.with_overrides(
            _relative_paths(config.presets[preset], source.parent)
        )
    return settings
