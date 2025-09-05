"""Shared test fixtures and utilities for pydanticonf tests."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Generator

import pytest
import yaml


@pytest.fixture
def temp_yaml_file() -> Generator[Path, None, None]:
    """Create a temporary YAML file for testing."""
    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)
    try:
        yield temp_path
    finally:
        if temp_path.exists():
            temp_path.unlink()


@pytest.fixture
def valid_yaml_config(temp_yaml_file: Path) -> Path:
    """Create a valid YAML configuration file."""
    config_data = {
        "app_name": "TestApp",
        "debug": True,
        "port": 8000,
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "testdb",
            "user": "testuser",
        },
        "features": ["auth", "api", "websocket"],
        "max_connections": 100,
    }
    temp_yaml_file.write_text(yaml.dump(config_data))
    return temp_yaml_file


@pytest.fixture
def nested_yaml_config(temp_yaml_file: Path) -> Path:
    """Create a deeply nested YAML configuration file."""
    config_data = {
        "level1": {
            "level2": {
                "level3": {
                    "value": "deep_value",
                    "number": 42,
                    "enabled": True,
                }
            },
            "items": [
                {"id": 1, "name": "item1"},
                {"id": 2, "name": "item2"},
            ],
        },
        "metadata": {
            "version": "1.0.0",
            "author": "test",
        },
    }
    temp_yaml_file.write_text(yaml.dump(config_data))
    return temp_yaml_file


@pytest.fixture
def invalid_yaml_file(temp_yaml_file: Path) -> Path:
    """Create an invalid YAML file for error testing."""
    temp_yaml_file.write_text("invalid: yaml: content: [unclosed")
    return temp_yaml_file


@pytest.fixture
def empty_yaml_file(temp_yaml_file: Path) -> Path:
    """Create an empty YAML file."""
    temp_yaml_file.write_text("")
    return temp_yaml_file


@pytest.fixture
def yaml_with_env_vars(temp_yaml_file: Path) -> Path:
    """Create a YAML file with environment variable references."""
    config_data = {
        "app_name": "${APP_NAME:DefaultApp}",
        "debug": "${DEBUG:false}",
        "port": "${PORT:8000}",
        "database_url": "${DATABASE_URL}",
    }
    temp_yaml_file.write_text(yaml.dump(config_data))
    return temp_yaml_file


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clean environment variables before each test."""
    env_vars_to_clean = [
        "APP_NAME",
        "DEBUG",
        "PORT",
        "DATABASE_URL",
        "TEST_VAR",
        "TEST_NUMBER",
        "TEST_BOOL",
    ]
    for var in env_vars_to_clean:
        monkeypatch.delenv(var, raising=False)
    return


@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Set up mock environment variables."""
    env_vars = {
        "APP_NAME": "EnvApp",
        "DEBUG": "true",
        "PORT": "9000",
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "TEST_VAR": "test_value",
        "TEST_NUMBER": "42",
        "TEST_BOOL": "true",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def dotenv_file(tmp_path: Path) -> Path:
    """Create a .env file for testing."""
    env_file = tmp_path / ".env"
    env_content = """
APP_NAME=DotenvApp
DEBUG=false
PORT=7000
DATABASE_URL=sqlite:///test.db
SECRET_KEY=supersecret123
"""
    env_file.write_text(env_content)
    return env_file


def assert_dict_subset(subset: dict[str, Any], superset: dict[str, Any]) -> None:
    """Assert that all items in subset exist in superset with same values."""
    for key, value in subset.items():
        assert key in superset, f"Key '{key}' not found in superset"
        if isinstance(value, dict) and isinstance(superset[key], dict):
            assert_dict_subset(value, superset[key])
        else:
            assert superset[key] == value, f"Value mismatch for key '{key}': {superset[key]} != {value}"
