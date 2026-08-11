"""Tests for cateroo.config module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from cateroo.config import Config, load_config


class TestConfig:
    """Tests for Config dataclass."""

    def test_all_fields_present(self) -> None:
        config = Config(
            cateroo_url="https://example.com",
            cateroo_user="user@example.com",
            cateroo_password="secret",
            ics_output_path="./lunch.ics",
            db_path="./test.db",
        )
        assert config.cateroo_url == "https://example.com"
        assert config.cateroo_user == "user@example.com"
        assert config.cateroo_password == "secret"
        assert config.ics_output_path == "./lunch.ics"
        assert config.db_path == "./test.db"


@patch("cateroo.config.load_dotenv")
class TestLoadConfig:
    """Tests for load_config function."""

    def _full_env(self) -> dict[str, str]:
        return {
            "CATEROO_URL": "https://mobile-kantine.essenbestellen.net",
            "CATEROO_USER": "user@example.com",
            "CATEROO_PASSWORD": "pass123",
            "ICS_OUTPUT_PATH": "/tmp/lunch.ics",
            "DB_PATH": "/tmp/test.db",
        }

    def test_loads_all_values(self, _mock_dotenv: MagicMock) -> None:
        with patch.dict(os.environ, self._full_env(), clear=True):
            config = load_config()
        assert config.cateroo_url == "https://mobile-kantine.essenbestellen.net"
        assert config.cateroo_user == "user@example.com"
        assert config.cateroo_password == "pass123"
        assert config.ics_output_path == "/tmp/lunch.ics"
        assert config.db_path == "/tmp/test.db"

    def test_default_ics_output_path(self, _mock_dotenv: MagicMock) -> None:
        env = self._full_env()
        del env["ICS_OUTPUT_PATH"]
        with patch.dict(os.environ, env, clear=True):
            config = load_config()
        assert config.ics_output_path == "./cateroo.ics"

    def test_default_db_path(self, _mock_dotenv: MagicMock) -> None:
        env = self._full_env()
        del env["DB_PATH"]
        with patch.dict(os.environ, env, clear=True):
            config = load_config()
        assert config.db_path == "./cateroo.db"

    def test_missing_cateroo_url_raises(self, _mock_dotenv: MagicMock) -> None:
        env = self._full_env()
        del env["CATEROO_URL"]
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="CATEROO_URL"),
        ):
            load_config()

    def test_missing_cateroo_user_raises(self, _mock_dotenv: MagicMock) -> None:
        env = self._full_env()
        del env["CATEROO_USER"]
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="CATEROO_USER"),
        ):
            load_config()

    def test_missing_cateroo_password_raises(self, _mock_dotenv: MagicMock) -> None:
        env = self._full_env()
        del env["CATEROO_PASSWORD"]
        with (
            patch.dict(os.environ, env, clear=True),
            pytest.raises(ValueError, match="CATEROO_PASSWORD"),
        ):
            load_config()
