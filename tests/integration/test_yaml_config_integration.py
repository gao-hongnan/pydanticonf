"""Integration tests for YAML configuration loading with BaseSettingsWithYaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import SettingsConfigDict

from pydanticonf.settings import BaseSettingsWithYaml


class DatabaseConfig(BaseModel):
    """Database configuration model."""

    host: str = "localhost"
    port: int = 5432
    name: str = "testdb"
    user: str = "user"
    ssl_enabled: bool = False


class CacheConfig(BaseModel):
    """Cache configuration model."""

    provider: str = "memory"
    host: str = "localhost"
    port: int = 6379
    ttl: int = 300
    max_connections: int = 10


class AppSettings(BaseSettingsWithYaml):
    """Complete application settings for testing."""

    app_name: str = "DefaultApp"
    debug: bool = False
    port: int = 8000
    host: str = "127.0.0.1"
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig | None = None
    features: list[str] = Field(default_factory=list)
    max_connections: int = 100
    timeout: int = 30

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )


class TestYamlConfigIntegration:
    """Integration tests for YAML configuration loading."""

    def test_load_yaml_config_from_file(self, valid_yaml_config: Path) -> None:
        """Test loading configuration from a YAML file."""

        class Settings(BaseSettingsWithYaml):
            app_name: str = "Default"
            debug: bool = False
            port: int = 3000
            database: dict[str, Any] = Field(default_factory=dict)
            features: list[str] = Field(default_factory=list)
            max_connections: int = 50

            model_config = SettingsConfigDict(
                yaml_file=str(valid_yaml_config),
            )

        settings = Settings()

        assert settings.app_name == "TestApp"
        assert settings.debug is True
        assert settings.port == 8000
        assert settings.database["host"] == "localhost"
        assert settings.database["port"] == 5432
        assert settings.database["name"] == "testdb"
        assert settings.features == ["auth", "api", "websocket"]
        assert settings.max_connections == 100

    def test_yaml_with_nested_models(self, temp_yaml_file: Path) -> None:
        """Test YAML loading with nested pydantic models."""
        config_data = {
            "app_name": "NestedApp",
            "debug": True,
            "database": {
                "host": "db.example.com",
                "port": 5432,
                "name": "production",
                "user": "admin",
                "ssl_enabled": True,
            },
            "cache": {
                "provider": "redis",
                "host": "redis.example.com",
                "port": 6380,
                "ttl": 600,
                "max_connections": 50,
            },
        }
        temp_yaml_file.write_text(yaml.dump(config_data))

        class Settings(AppSettings):
            model_config = SettingsConfigDict(
                yaml_file=str(temp_yaml_file),
            )

        settings = Settings()

        assert settings.app_name == "NestedApp"
        assert settings.debug is True
        assert settings.database.host == "db.example.com"
        assert settings.database.port == 5432
        assert settings.database.ssl_enabled is True
        assert settings.cache is not None
        assert settings.cache.provider == "redis"
        assert settings.cache.ttl == 600

    def test_environment_override_yaml(
        self,
        valid_yaml_config: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that environment variables override YAML values."""

        class Settings(BaseSettingsWithYaml):
            app_name: str = "Default"
            debug: bool = False
            port: int = 3000

            model_config = SettingsConfigDict(
                yaml_file=str(valid_yaml_config),
                env_prefix="TEST_",
                extra="allow",
            )

        monkeypatch.setenv("TEST_APP_NAME", "EnvOverrideApp")
        monkeypatch.setenv("TEST_PORT", "9999")

        settings = Settings()

        assert settings.app_name == "EnvOverrideApp"
        assert settings.port == 9999
        assert settings.debug is True

    def test_dotenv_with_yaml(
        self,
        valid_yaml_config: Path,
        dotenv_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that dotenv and YAML work together correctly."""
        monkeypatch.chdir(dotenv_file.parent)

        class Settings(BaseSettingsWithYaml):
            app_name: str = "Default"
            debug: bool = True
            port: int = 3000
            secret_key: str = "default_secret"

            model_config = SettingsConfigDict(
                yaml_file=str(valid_yaml_config),
                env_file=".env",
                env_prefix="APP_",
                extra="allow",
            )

        settings = Settings()

        assert settings.app_name == "DotenvApp"
        assert settings.debug is False
        assert settings.port == 7000
        assert settings.secret_key == "supersecret123"

    def test_source_priority_order(
        self,
        temp_yaml_file: Path,
        dotenv_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test the priority order of configuration sources."""
        yaml_data = {
            "value": "from_yaml",
            "yaml_only": "yaml_value",
        }
        temp_yaml_file.write_text(yaml.dump(yaml_data))

        monkeypatch.chdir(dotenv_file.parent)
        dotenv_content = "TEST_VALUE=from_dotenv\nTEST_DOTENV_ONLY=dotenv_value"
        (dotenv_file.parent / ".env").write_text(dotenv_content)

        monkeypatch.setenv("TEST_VALUE", "from_env")
        monkeypatch.setenv("TEST_ENV_ONLY", "env_value")

        class Settings(BaseSettingsWithYaml):
            value: str = "default"
            yaml_only: str = "default"
            dotenv_only: str = "default"
            env_only: str = "default"

            model_config = SettingsConfigDict(
                yaml_file=str(temp_yaml_file),
                env_file=".env",
                env_prefix="TEST_",
            )

        settings = Settings(value="from_init")

        assert settings.value == "from_init"
        assert settings.yaml_only == "yaml_value"
        assert settings.dotenv_only == "dotenv_value"
        assert settings.env_only == "env_value"

    def test_missing_yaml_file(self) -> None:
        """Test behavior when YAML file doesn't exist - should use defaults."""

        class Settings(BaseSettingsWithYaml):
            app_name: str = "Default"
            port: int = 8000

            model_config = SettingsConfigDict(
                yaml_file="nonexistent.yaml",
            )

        # When YAML file doesn't exist, it should just use defaults
        settings = Settings()
        assert settings.app_name == "Default"
        assert settings.port == 8000

    def test_invalid_yaml_syntax(self, invalid_yaml_file: Path) -> None:
        """Test behavior with invalid YAML syntax."""

        class Settings(BaseSettingsWithYaml):
            app_name: str = "Default"

            model_config = SettingsConfigDict(
                yaml_file=str(invalid_yaml_file),
            )

        from yaml.scanner import ScannerError

        with pytest.raises(ScannerError):
            Settings()

    def test_empty_yaml_file(self, empty_yaml_file: Path) -> None:
        """Test behavior with empty YAML file."""

        class Settings(BaseSettingsWithYaml):
            app_name: str = "Default"
            port: int = 8000

            model_config = SettingsConfigDict(
                yaml_file=str(empty_yaml_file),
            )

        settings = Settings()
        assert settings.app_name == "Default"
        assert settings.port == 8000

    def test_complex_nested_yaml(self, nested_yaml_config: Path) -> None:
        """Test loading complex nested YAML structures."""

        class Level3Config(BaseModel):
            value: str
            number: int
            enabled: bool

        class Level2Config(BaseModel):
            level3: Level3Config

        class Level1Config(BaseModel):
            level2: Level2Config
            items: list[dict[str, Any]]

        class MetadataConfig(BaseModel):
            version: str
            author: str

        class ComplexSettings(BaseSettingsWithYaml):
            level1: Level1Config | None = None
            metadata: MetadataConfig | None = None

            model_config = SettingsConfigDict(
                yaml_file=str(nested_yaml_config),
            )

        settings = ComplexSettings()

        assert settings.level1 is not None
        assert settings.level1.level2.level3.value == "deep_value"
        assert settings.level1.level2.level3.number == 42
        assert settings.level1.level2.level3.enabled is True
        assert len(settings.level1.items) == 2
        assert settings.level1.items[0]["name"] == "item1"
        assert settings.metadata is not None
        assert settings.metadata.version == "1.0.0"

    def test_yaml_with_list_types(self, temp_yaml_file: Path) -> None:
        """Test YAML loading with list types."""
        config_data = {
            "servers": ["server1.com", "server2.com", "server3.com"],
            "ports": [8000, 8001, 8002],
            "features": [
                {"name": "auth", "enabled": True},
                {"name": "api", "enabled": False},
            ],
        }
        temp_yaml_file.write_text(yaml.dump(config_data))

        class FeatureConfig(BaseModel):
            name: str
            enabled: bool

        class Settings(BaseSettingsWithYaml):
            servers: list[str] = Field(default_factory=list)
            ports: list[int] = Field(default_factory=list)
            features: list[FeatureConfig] = Field(default_factory=list)

            model_config = SettingsConfigDict(
                yaml_file=str(temp_yaml_file),
            )

        settings = Settings()

        assert settings.servers == ["server1.com", "server2.com", "server3.com"]
        assert settings.ports == [8000, 8001, 8002]
        assert len(settings.features) == 2
        assert settings.features[0].name == "auth"
        assert settings.features[0].enabled is True

    def test_yaml_encoding(self, temp_yaml_file: Path) -> None:
        """Test YAML file with different encoding."""
        config_data = {"app_name": "TestApp", "description": "Application de test"}
        yaml_content = yaml.dump(config_data, allow_unicode=True)
        temp_yaml_file.write_text(yaml_content, encoding="utf-8")

        class Settings(BaseSettingsWithYaml):
            app_name: str = "Default"
            description: str = ""

            model_config = SettingsConfigDict(
                yaml_file=str(temp_yaml_file),
                yaml_file_encoding="utf-8",
            )

        settings = Settings()
        assert settings.app_name == "TestApp"
        assert settings.description == "Application de test"

    def test_yaml_with_env_nested_delimiter(
        self,
        temp_yaml_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test YAML with environment variable nested delimiter."""
        config_data = {
            "database": {
                "host": "localhost",
                "port": 5432,
            },
        }
        temp_yaml_file.write_text(yaml.dump(config_data))

        monkeypatch.setenv("APP_DATABASE__HOST", "env.db.com")
        monkeypatch.setenv("APP_DATABASE__PORT", "3306")

        class Settings(AppSettings):
            model_config = SettingsConfigDict(
                yaml_file=str(temp_yaml_file),
                env_prefix="APP_",
                env_nested_delimiter="__",
            )

        settings = Settings()

        assert settings.database.host == "env.db.com"
        assert settings.database.port == 3306

    def test_yaml_partial_config(self, temp_yaml_file: Path) -> None:
        """Test YAML with partial configuration (some fields not in YAML)."""
        config_data = {
            "app_name": "PartialApp",
            "port": 9000,
        }
        temp_yaml_file.write_text(yaml.dump(config_data))

        class Settings(AppSettings):
            model_config = SettingsConfigDict(
                yaml_file=str(temp_yaml_file),
            )

        settings = Settings()

        assert settings.app_name == "PartialApp"
        assert settings.port == 9000
        assert settings.debug is False
        assert settings.host == "127.0.0.1"
        assert settings.database.host == "localhost"

    def test_fixtures_directory_configs(self) -> None:
        """Test loading real fixture YAML files."""
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        valid_config = fixtures_dir / "valid_config.yaml"

        if valid_config.exists():

            class Settings(BaseSettingsWithYaml):
                app_name: str = "Default"
                debug: bool = True
                port: int = 3000
                host: str = "localhost"
                timeout: int = 10

                model_config = SettingsConfigDict(
                    yaml_file=str(valid_config),
                    extra="allow",
                )

            settings = Settings()

            assert settings.app_name == "ProductionApp"
            assert settings.debug is False
            assert settings.port == 8080
            assert settings.host == "0.0.0.0"
            assert settings.timeout == 30
