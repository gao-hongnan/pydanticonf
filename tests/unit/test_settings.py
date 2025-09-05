"""Unit tests for pydanticonf.settings module."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import Field
from pydantic_settings import SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource

from pydanticonf.settings import BaseSettingsWithYaml


class TestBaseSettingsWithYaml:
    """Test cases for BaseSettingsWithYaml class."""

    def test_class_inheritance(self) -> None:
        """Test that BaseSettingsWithYaml properly inherits from BaseSettings."""
        from pydantic_settings import BaseSettings

        assert issubclass(BaseSettingsWithYaml, BaseSettings)

    def test_settings_customise_sources_without_yaml(self) -> None:
        """Test settings_customise_sources when no YAML file is configured."""

        class TestSettings(BaseSettingsWithYaml):
            """Test settings without YAML configuration."""

            app_name: str = "DefaultApp"
            debug: bool = False
            model_config = SettingsConfigDict(env_prefix="TEST_")

        init_settings = MagicMock(spec=PydanticBaseSettingsSource)
        env_settings = MagicMock(spec=PydanticBaseSettingsSource)
        dotenv_settings = MagicMock(spec=PydanticBaseSettingsSource)
        file_secret_settings = MagicMock(spec=PydanticBaseSettingsSource)

        with patch.object(BaseSettingsWithYaml.__base__, "settings_customise_sources") as mock_parent:
            mock_parent.return_value = (
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
            )

            sources = TestSettings.settings_customise_sources(
                TestSettings,
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
            )

            mock_parent.assert_called_once()
            assert sources == (init_settings, env_settings, dotenv_settings, file_secret_settings)

    def test_settings_customise_sources_with_yaml(self, temp_yaml_file: Path) -> None:
        """Test settings_customise_sources when YAML file is configured."""

        class TestSettings(BaseSettingsWithYaml):
            """Test settings with YAML configuration."""

            app_name: str = "DefaultApp"
            debug: bool = False
            model_config = SettingsConfigDict(
                env_prefix="TEST_",
                yaml_file=str(temp_yaml_file),
            )

        init_settings = MagicMock(spec=PydanticBaseSettingsSource)
        env_settings = MagicMock(spec=PydanticBaseSettingsSource)
        dotenv_settings = MagicMock(spec=PydanticBaseSettingsSource)
        file_secret_settings = MagicMock(spec=PydanticBaseSettingsSource)

        with patch("pydanticonf.settings.YamlConfigSettingsSource") as mock_yaml_source:
            mock_yaml_instance = MagicMock(spec=PydanticBaseSettingsSource)
            mock_yaml_source.return_value = mock_yaml_instance

            sources = TestSettings.settings_customise_sources(
                TestSettings,
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
            )

            mock_yaml_source.assert_called_once_with(
                TestSettings,
                yaml_file=str(temp_yaml_file),
                yaml_file_encoding="utf-8",
            )

            assert len(sources) == 5
            assert sources[0] is init_settings
            assert sources[1] is env_settings
            assert sources[2] is dotenv_settings
            assert sources[3] is file_secret_settings
            assert sources[4] is mock_yaml_instance

    def test_settings_customise_sources_with_custom_encoding(self, temp_yaml_file: Path) -> None:
        """Test settings_customise_sources with custom YAML encoding."""

        class TestSettings(BaseSettingsWithYaml):
            """Test settings with custom YAML encoding."""

            app_name: str = "DefaultApp"
            model_config = SettingsConfigDict(
                yaml_file=str(temp_yaml_file),
                yaml_file_encoding="latin-1",
            )

        init_settings = MagicMock(spec=PydanticBaseSettingsSource)
        env_settings = MagicMock(spec=PydanticBaseSettingsSource)
        dotenv_settings = MagicMock(spec=PydanticBaseSettingsSource)
        file_secret_settings = MagicMock(spec=PydanticBaseSettingsSource)

        with patch("pydanticonf.settings.YamlConfigSettingsSource") as mock_yaml_source:
            TestSettings.settings_customise_sources(
                TestSettings,
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
            )

            mock_yaml_source.assert_called_once_with(
                TestSettings,
                yaml_file=str(temp_yaml_file),
                yaml_file_encoding="latin-1",
            )

    def test_source_priority_order(self, temp_yaml_file: Path) -> None:
        """Test that sources are returned in the correct priority order."""

        class TestSettings(BaseSettingsWithYaml):
            """Test settings to verify source priority."""

            value: str = "default"
            model_config = SettingsConfigDict(
                yaml_file=str(temp_yaml_file),
            )

        sources = TestSettings.settings_customise_sources(
            TestSettings,
            MagicMock(spec=PydanticBaseSettingsSource),
            MagicMock(spec=PydanticBaseSettingsSource),
            MagicMock(spec=PydanticBaseSettingsSource),
            MagicMock(spec=PydanticBaseSettingsSource),
        )

        assert len(sources) == 5
        source_names = [type(source).__name__ for source in sources]
        assert source_names[0] == "MagicMock"
        assert source_names[1] == "MagicMock"
        assert source_names[2] == "MagicMock"
        assert source_names[3] == "MagicMock"

    def test_multiple_yaml_configs(self) -> None:
        """Test that each settings class can have its own YAML configuration."""
        yaml_file1 = "config1.yaml"
        yaml_file2 = "config2.yaml"

        class Settings1(BaseSettingsWithYaml):
            """First settings class."""

            value1: str
            model_config = SettingsConfigDict(yaml_file=yaml_file1)

        class Settings2(BaseSettingsWithYaml):
            """Second settings class."""

            value2: str
            model_config = SettingsConfigDict(yaml_file=yaml_file2)

        assert Settings1.model_config.get("yaml_file") == yaml_file1
        assert Settings2.model_config.get("yaml_file") == yaml_file2

    def test_nested_settings_class(self) -> None:
        """Test BaseSettingsWithYaml with nested pydantic models."""

        from pydantic import BaseModel

        class DatabaseConfig(BaseModel):
            """Database configuration model."""

            host: str = "localhost"
            port: int = 5432
            name: str = "testdb"

        class AppSettings(BaseSettingsWithYaml):
            """Application settings with nested config."""

            app_name: str = "TestApp"
            database: DatabaseConfig = Field(default_factory=DatabaseConfig)
            features: list[str] = Field(default_factory=list)

        settings = AppSettings()
        assert settings.app_name == "TestApp"
        assert settings.database.host == "localhost"
        assert settings.database.port == 5432
        assert settings.features == []

    def test_field_validators(self) -> None:
        """Test that field validators work with BaseSettingsWithYaml."""

        from pydantic import field_validator

        class ValidatedSettings(BaseSettingsWithYaml):
            """Settings with field validation."""

            port: int = 8000
            app_name: str = "App"

            @field_validator("port")
            @classmethod
            def validate_port(cls, v: int) -> int:
                """Validate port is in valid range."""
                if not 1 <= v <= 65535:
                    msg = "Port must be between 1 and 65535"
                    raise ValueError(msg)
                return v

            @field_validator("app_name")
            @classmethod
            def validate_app_name(cls, v: str) -> str:
                """Validate app name is not empty."""
                if not v.strip():
                    msg = "App name cannot be empty"
                    raise ValueError(msg)
                return v.strip()

        settings = ValidatedSettings(port=8080, app_name="  TestApp  ")
        assert settings.port == 8080
        assert settings.app_name == "TestApp"

        with pytest.raises(ValueError, match="Port must be between"):
            ValidatedSettings(port=70000)

        with pytest.raises(ValueError, match="App name cannot be empty"):
            ValidatedSettings(app_name="  ")

    def test_model_config_preservation(self) -> None:
        """Test that other model_config options are preserved."""

        class ConfiguredSettings(BaseSettingsWithYaml):
            """Settings with various model_config options."""

            api_key: str = "secret"
            debug_mode: bool = False

            model_config = SettingsConfigDict(
                env_prefix="MYAPP_",
                case_sensitive=False,
                env_nested_delimiter="__",
                yaml_file="config.yaml",
                extra="forbid",
            )

        config = ConfiguredSettings.model_config
        assert config.get("env_prefix") == "MYAPP_"
        assert config.get("case_sensitive") is False
        assert config.get("env_nested_delimiter") == "__"
        assert config.get("yaml_file") == "config.yaml"
        assert config.get("extra") == "forbid"

    def test_type_hints_and_annotations(self) -> None:
        """Test that type hints and annotations are properly handled."""

        class TypedSettings(BaseSettingsWithYaml):
            """Settings with various type hints."""

            required_str: str
            optional_str: str | None = None
            int_value: int = 42
            float_value: float = 3.14
            bool_value: bool = True
            list_value: list[int] = Field(default_factory=lambda: [1, 2, 3])
            dict_value: dict[str, Any] = Field(default_factory=dict)

        settings = TypedSettings(required_str="test")
        assert settings.required_str == "test"
        assert settings.optional_str is None
        assert settings.int_value == 42
        assert settings.float_value == 3.14
        assert settings.bool_value is True
        assert settings.list_value == [1, 2, 3]
        assert settings.dict_value == {}
