from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource, YamlConfigSettingsSource

# Per-call YAML override — set by ``__init__`` before delegating to
# ``BaseSettings.__init__``, read by ``settings_customise_sources`` (a
# classmethod that has no access to instance state). ContextVar is chosen over
# ``threading.local`` so concurrent ``asyncio`` tasks on the same thread each
# see their own override.
_yaml_override: ContextVar[tuple[str, str] | None] = ContextVar("pydanticonf_yaml_override", default=None)


class BaseSettingsWithYaml(BaseSettings):
    """Base settings class with YAML configuration support.

    YAML path resolution (highest precedence first):

    1. ``_yaml_file=`` init kwarg (per-instance runtime override)
    2. ``model_config["yaml_file"]`` (class-level default)
    3. No YAML source if neither is set

    Source priority within pydantic-settings is preserved: env vars still
    override YAML values, matching the convention used by ``_env_file=``.

    Example:
        >>> class Settings(BaseSettingsWithYaml):
        ...     model_config = SettingsConfigDict(yaml_file="defaults.yaml")
        ...     key: str = "builtin"
        >>> Settings()                                 # reads defaults.yaml
        >>> Settings(_yaml_file="overrides.yaml")      # per-instance override
    """

    def __init__(
        self,
        _yaml_file: str | Path | None = None,
        _yaml_file_encoding: str | None = None,
        **values: Any,
    ) -> None:
        if _yaml_file is None:
            super().__init__(**values)
            return
        token = _yaml_override.set((str(_yaml_file), _yaml_file_encoding or "utf-8"))
        try:
            super().__init__(**values)
        finally:
            _yaml_override.reset(token)

    @classmethod
    def settings_customise_sources(
        cls: type[BaseSettingsWithYaml],
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources to include YAML support."""
        override = _yaml_override.get()
        if override is not None:
            yaml_file: str | None = override[0]
            yaml_file_encoding: str = override[1]
        else:
            config: SettingsConfigDict = cls.model_config
            yaml_file = config.get("yaml_file")  # type: ignore[assignment]
            yaml_file_encoding = config.get("yaml_file_encoding") or "utf-8"

        if not yaml_file:
            return super().settings_customise_sources(
                settings_cls=settings_cls,
                init_settings=init_settings,
                env_settings=env_settings,
                dotenv_settings=dotenv_settings,
                file_secret_settings=file_secret_settings,
            )

        yaml_settings = YamlConfigSettingsSource(
            settings_cls,
            yaml_file=yaml_file,
            yaml_file_encoding=yaml_file_encoding,
        )

        return (init_settings, env_settings, dotenv_settings, file_secret_settings, yaml_settings)
