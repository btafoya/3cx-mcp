"""
Configuration management for 3CX Debugging MCP Server.

Loads configuration from environment variables with sensible defaults
for running on a 3CX Professional server.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class DatabaseConfig:
    """PostgreSQL database connection configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "3cxpbx"
    user: str = "3cxpbx"
    password: Optional[str] = None
    socket_dir: str = "/var/run/postgresql"
    use_socket: bool = True
    pool_size: int = 5


@dataclass
class LogConfig:
    """3CX log file configuration."""
    main_log_path: str = "/var/lib/3cxpbx/Bin/3CXPhoneSystem.log"
    log_dir: str = "/var/lib/3cxpbx/Bin"
    instance_log_dir: str = "/var/lib/3cxpbx/Instance1/Data/Logs"
    encoding: str = "utf-8"
    rotation_pattern: str = "3CXPhoneSystem-*.log"


@dataclass
class ServerConfig:
    """Server configuration."""
    mcp_name: str = "3cx-debugging"
    log_level: str = "INFO"
    enable_write_operations: bool = True
    audit_log_path: str = "/var/log/3cx-mcp-debugging/audit.log"


@dataclass
class Config:
    """Complete configuration."""
    database: DatabaseConfig
    logs: LogConfig
    server: ServerConfig

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            database=DatabaseConfig(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                database=os.getenv("DB_NAME", "3cxpbx"),
                user=os.getenv("DB_USER", "3cxpbx"),
                password=os.getenv("DB_PASSWORD"),
                socket_dir=os.getenv("DB_SOCKET_DIR", "/var/run/postgresql"),
                use_socket=os.getenv("DB_USE_SOCKET", "true").lower() == "true",
            ),
            logs=LogConfig(
                main_log_path=os.getenv("LOG_PATH", "/var/lib/3cxpbx/Bin/3CXPhoneSystem.log"),
                log_dir=os.getenv("LOG_DIR", "/var/lib/3cxpbx/Bin"),
            ),
            server=ServerConfig(
                mcp_name=os.getenv("MCP_NAME", "3cx-debugging"),
                enable_write_operations=os.getenv("ENABLE_WRITES", "true").lower() == "true",
            )
        )

    def validate(self) -> None:
        """Validate configuration."""
        if self.database.use_socket:
            if not Path(self.database.socket_dir).exists():
                raise ValueError(f"PostgreSQL socket directory not found: {self.database.socket_dir}")
        else:
            if not self.database.password:
                raise ValueError("Database password required when not using socket")

        if not Path(self.logs.main_log_path).exists():
            raise ValueError(f"Main log file not found: {self.logs.main_log_path}")

        Path(self.server.audit_log_path).parent.mkdir(parents=True, exist_ok=True)