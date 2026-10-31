"""
Unit tests for database connection configuration and parameter handling.
"""

import os
from unittest.mock import patch, MagicMock
import pytest
from backend.db import get_db_config, _str_to_bool, get_connection


def test_str_to_bool():
    assert _str_to_bool("true") is True
    assert _str_to_bool("TRUE") is True
    assert _str_to_bool("1") is True
    assert _str_to_bool("yes") is True
    assert _str_to_bool("false") is False
    assert _str_to_bool("0") is False
    assert _str_to_bool(None, default=False) is False
    assert _str_to_bool(None, default=True) is True


def test_get_db_config_defaults():
    with patch.dict(os.environ, {}, clear=True):
        config = get_db_config()
        assert config["host"] == "localhost"
        assert config["port"] == 8563
        assert config["user"] == "sys"
        assert config["password"] == "exasol"
        assert config["schema"] == "OPSLENS"
        assert config["verify_cert"] is False
        assert config["encryption"] is True
        assert config["dsn"] == "localhost:8563"


def test_get_db_config_custom():
    env = {
        "EXA_HOST": "exasol.example.com",
        "EXA_PORT": "9563",
        "EXA_USER": "test_user",
        "EXA_PASSWORD": "secret_password",
        "EXA_SCHEMA": "CUSTOM_OPS",
        "EXA_VERIFY_CERT": "true",
        "EXA_ENCRYPTION": "false",
    }
    with patch.dict(os.environ, env, clear=True):
        config = get_db_config()
        assert config["host"] == "exasol.example.com"
        assert config["port"] == 9563
        assert config["user"] == "test_user"
        assert config["verify_cert"] is True
        assert config["encryption"] is False
        assert config["dsn"] == "exasol.example.com:9563"


@patch("backend.db.pyexasol.connect")
def test_get_connection_verify_cert_false(mock_connect):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    env = {
        "EXA_HOST": "localhost",
        "EXA_PORT": "8563",
        "EXA_USER": "sys",
        "EXA_PASSWORD": "exasol",
        "EXA_VERIFY_CERT": "false",
        "EXA_ENCRYPTION": "true",
    }
    with patch.dict(os.environ, env, clear=True):
        conn = get_connection()
        assert conn == mock_conn
        args, kwargs = mock_connect.call_args
        assert kwargs["dsn"] == "localhost:8563"
        assert "websocket_sslopt" in kwargs
        # Verify CERT_NONE was set
        assert kwargs["websocket_sslopt"]["cert_reqs"] == 0  # ssl.CERT_NONE is 0
