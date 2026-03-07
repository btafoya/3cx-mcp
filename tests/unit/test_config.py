"""
Unit tests for configuration management.
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import (
    Config,
    DatabaseConfig,
    LogConfig,
    ServerConfig,
)


class TestDatabaseConfig:
    """Tests for DatabaseConfig."""

    def test_database_config_defaults(self):
        """Test DatabaseConfig default values."""
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "3cxpbx"
        assert config.user == "3cxpbx"
        assert config.password is None
        assert config.socket_dir == "/var/run/postgresql"
        assert config.use_socket is True
        assert config.pool_size == 5

    def test_database_config_custom(self):
        """Test DatabaseConfig with custom values."""
        config = DatabaseConfig(
            host="db.example.com",
            port=5433,
            database="custom_db",
            user="custom_user",
            password="secret123",
            use_socket=False,
            pool_size=10,
        )
        assert config.host == "db.example.com"
        assert config.port == 5433
        assert config.database == "custom_db"
        assert config.user == "custom_user"
        assert config.password == "secret123"
        assert config.use_socket is False
        assert config.pool_size == 10


class TestLogConfig:
    """Tests for LogConfig."""

    def test_log_config_defaults(self):
        """Test LogConfig default values."""
        config = LogConfig()
        assert config.main_log_path == "/var/lib/3cxpbx/Bin/3CXPhoneSystem.log"
        assert config.log_dir == "/var/lib/3cxpbx/Bin"
        assert config.instance_log_dir == "/var/lib/3cxpbx/Instance1/Data/Logs"
        assert config.encoding == "utf-8"

    def test_log_config_custom(self):
        """Test LogConfig with custom values."""
        config = LogConfig(
            main_log_path="/custom/path/3CXPhoneSystem.log",
            log_dir="/custom/path",
            instance_log_dir="/custom/instance",
            encoding="latin-1",
        )
        assert config.main_log_path == "/custom/path/3CXPhoneSystem.log"
        assert config.log_dir == "/custom/path"
        assert config.instance_log_dir == "/custom/instance"
        assert config.encoding == "latin-1"


class TestServerConfig:
    """Tests for ServerConfig."""

    def test_server_config_defaults(self):
        """Test ServerConfig default values."""
        config = ServerConfig()
        assert config.mcp_name == "3cx-debugging"
        assert config.log_level == "INFO"
        assert config.enable_write_operations is True

    def test_server_config_custom(self):
        """Test ServerConfig with custom values."""
        config = ServerConfig(
            mcp_name="custom-server",
            log_level="DEBUG",
            enable_write_operations=False,
        )
        assert config.mcp_name == "custom-server"
        assert config.log_level == "DEBUG"
        assert config.enable_write_operations is False


class TestConfig:
    """Tests for Config."""

    def test_config_from_env_defaults(self, clean_env):
        """Test Config.from_env() with default environment."""
        # Clear test-specific env vars for this test to use actual defaults
        os.environ.pop("DB_NAME", None)
        os.environ.pop("DB_USER", None)
        os.environ.pop("MCP_NAME", None)
        os.environ.pop("DB_USE_SOCKET", None)
        os.environ.pop("ENABLE_WRITES", None)

        config = Config.from_env()

        assert config.database.host == "localhost"
        assert config.database.database == "3cxpbx"
        assert config.database.user == "3cxpbx"
        assert config.database.use_socket is True

        assert config.logs.main_log_path == "/var/lib/3cxpbx/Bin/3CXPhoneSystem.log"

        assert config.server.mcp_name == "3cx-debugging"
        assert config.server.enable_write_operations is True

        # Restore test env vars
        os.environ["DB_NAME"] = "test_3cxpbx"
        os.environ["DB_USER"] = "test_user"
        os.environ["MCP_NAME"] = "test-3cx-debugging"
        os.environ["DB_USE_SOCKET"] = "false"
        os.environ["ENABLE_WRITES"] = "false"

    def test_config_from_env_custom(self, clean_env):
        """Test Config.from_env() with custom environment."""
        os.environ["DB_HOST"] = "custom.db"
        os.environ["DB_PORT"] = "5433"
        os.environ["DB_NAME"] = "custom_db"
        os.environ["DB_USER"] = "custom_user"
        os.environ["DB_PASSWORD"] = "custom_pass"
        os.environ["DB_USE_SOCKET"] = "false"
        os.environ["LOG_PATH"] = "/custom/log.log"
        os.environ["LOG_DIR"] = "/custom/dir"
        os.environ["MCP_NAME"] = "custom_mcp"
        os.environ["ENABLE_WRITES"] = "false"

        config = Config.from_env()

        assert config.database.host == "custom.db"
        assert config.database.port == 5433
        assert config.database.database == "custom_db"
        assert config.database.user == "custom_user"
        assert config.database.password == "custom_pass"
        assert config.database.use_socket is False

        assert config.logs.main_log_path == "/custom/log.log"
        assert config.logs.log_dir == "/custom/dir"

        assert config.server.mcp_name == "custom_mcp"
        assert config.server.enable_write_operations is False

    def test_config_validate_socket_exists(self, tmp_path, clean_env):
        """Test Config.validate() with existing socket directory."""
        socket_dir = tmp_path / "socket"
        socket_dir.mkdir()

        log_file = tmp_path / "test.log"
        log_file.write_text("test")

        audit_dir = tmp_path / "audit"
        audit_log_path = audit_dir / "audit.log"

        config = Config(
            database=DatabaseConfig(
                use_socket=True,
                socket_dir=str(socket_dir),
            ),
            logs=LogConfig(main_log_path=str(log_file)),
            server=ServerConfig(audit_log_path=str(audit_log_path)),
        )

        # Should not raise
        config.validate()

    def test_config_validate_socket_missing(self, clean_env):
        """Test Config.validate() with missing socket directory."""
        config = Config(
            database=DatabaseConfig(
                use_socket=True,
                socket_dir="/nonexistent/path",
            ),
            logs=LogConfig(main_log_path="/tmp/test.log"),
            server=ServerConfig(),
        )

        with pytest.raises(ValueError, match="PostgreSQL socket directory not found"):
            config.validate()

    def test_config_validate_tcp_no_password(self, clean_env):
        """Test Config.validate() with TCP but no password."""
        config = Config(
            database=DatabaseConfig(
                use_socket=False,
                password=None,
            ),
            logs=LogConfig(main_log_path="/tmp/test.log"),
            server=ServerConfig(),
        )

        with pytest.raises(ValueError, match="Database password required"):
            config.validate()

    def test_config_validate_log_missing(self, clean_env):
        """Test Config.validate() with missing log file."""
        config = Config(
            database=DatabaseConfig(
                use_socket=False,
                password="test",
            ),
            logs=LogConfig(main_log_path="/nonexistent/log.log"),
            server=ServerConfig(),
        )

        with pytest.raises(ValueError, match="Main log file not found"):
            config.validate()

    def test_config_validate_creates_audit_dir(self, tmp_path, clean_env):
        """Test Config.validate() creates audit directory."""
        log_file = tmp_path / "test.log"
        log_file.write_text("test")

        audit_dir = tmp_path / "audit"
        audit_log_path = audit_dir / "audit.log"

        config = Config(
            database=DatabaseConfig(
                use_socket=False,
                password="test",
            ),
            logs=LogConfig(main_log_path=str(log_file)),
            server=ServerConfig(audit_log_path=str(audit_log_path)),
        )

        config.validate()

        assert audit_dir.exists()

    def test_config_validate_tcp_with_password(self, clean_env, tmp_path):
        """Test Config.validate() with TCP and password."""
        log_file = tmp_path / "test.log"
        log_file.write_text("test")

        audit_dir = tmp_path / "audit"
        audit_log_path = audit_dir / "audit.log"

        config = Config(
            database=DatabaseConfig(
                use_socket=False,
                password="secret",
            ),
            logs=LogConfig(main_log_path=str(log_file)),
            server=ServerConfig(audit_log_path=str(audit_log_path)),
        )

        config.validate()