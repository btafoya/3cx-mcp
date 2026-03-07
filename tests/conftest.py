"""
Shared pytest configuration and fixtures for 3CX MCP Server tests.
"""
import asyncio
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Add project root to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config, DatabaseConfig, LogConfig, ServerConfig
from src.database.connection import DatabasePool, DatabaseError, QueryError
from src.logs.parser import LogParser, LogEntry, LogLevel, SipMethod


# ============================================================================
# Test Data Fixtures from Backup CSV Files
# ============================================================================

@pytest.fixture(scope="session")
def backup_dir() -> Path:
    """Path to the backup directory containing test data."""
    return Path(__file__).parent.parent / "backup"


@pytest.fixture(scope="session")
def sample_call_data(backup_dir: Path) -> list[dict]:
    """Sample call records from cl_calls.csv backup."""
    calls_file = backup_dir / "DbTables" / "cl_calls.csv"
    calls = []
    with open(calls_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            calls.append(dict(row))
            if len(calls) >= 20:  # Limit for test purposes
                break
    return calls


@pytest.fixture(scope="session")
def sample_queue_data(backup_dir: Path) -> list[dict]:
    """Sample queue call records from callcent_queuecalls.csv backup."""
    queue_file = backup_dir / "DbTables" / "callcent_queuecalls.csv"
    queues = []
    with open(queue_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            queues.append(dict(row))
            if len(queues) >= 10:
                break
    return queues


@pytest.fixture(scope="session")
def sample_audit_data(backup_dir: Path) -> list[dict]:
    """Sample audit log entries from audit_log.csv backup."""
    audit_file = backup_dir / "DbTables" / "audit_log.csv"
    audit_entries = []
    with open(audit_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            audit_entries.append(dict(row))
            if len(audit_entries) >= 15:
                break
    return audit_entries


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_database_config() -> DatabaseConfig:
    """Test database configuration (no actual connection)."""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="test_3cxpbx",
        user="test_user",
        password="test_pass",
        use_socket=False,  # Use TCP for tests
        pool_size=2,
    )


@pytest.fixture
def test_log_config(tmp_path: Path) -> LogConfig:
    """Test log configuration with temporary log file."""
    log_file = tmp_path / "test_3cx.log"
    log_file.write_text("2026-03-07 10:00:00.000 [1] INFO Test log message\n")
    return LogConfig(
        main_log_path=str(log_file),
        log_dir=str(tmp_path),
        instance_log_dir=str(tmp_path),
    )


@pytest.fixture
def test_server_config() -> ServerConfig:
    """Test server configuration."""
    return ServerConfig(
        mcp_name="test-3cx-debugging",
        log_level="DEBUG",
        enable_write_operations=False,
    )


@pytest.fixture
def test_config(
    test_database_config: DatabaseConfig,
    test_log_config: LogConfig,
    test_server_config: ServerConfig,
) -> Config:
    """Complete test configuration."""
    return Config(
        database=test_database_config,
        logs=test_log_config,
        server=test_server_config,
    )


# ============================================================================
# Mock Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_pool() -> AsyncMock:
    """Mock DatabasePool for testing."""
    mock = AsyncMock(spec=DatabasePool)
    mock.fetch = AsyncMock(return_value=[])
    mock.fetchone = AsyncMock(return_value=None)
    mock.fetchval = AsyncMock(return_value=1)
    mock.execute = AsyncMock(return_value="SELECT 1")
    mock.initialize = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
async def mock_db_connection(mock_db_pool: AsyncMock):
    """Context manager for mock database connection."""
    mock_db_pool._pool = MagicMock()
    yield mock_db_pool
    await mock_db_pool.close()


# ============================================================================
# Log Parser Fixtures
# ============================================================================

@pytest.fixture
def sample_log_file(tmp_path: Path) -> Path:
    """Create a sample log file for testing."""
    log_file = tmp_path / "test.log"
    log_content = """2026-03-07 10:00:00.000 [1] INFO System started
2026-03-07 10:00:01.123 [2] DEBUG INVITE sip:100@localhost
2026-03-07 10:00:02.456 [1] WARN Connection timeout
2026-03-07 10:00:03.789 [3] ERROR Call failed: timeout
2026-03-07 10:00:04.000 [1] INFO BYE sip:100@localhost
2026-03-07 10:00:05.000 [2] FATAL System crash
"""
    log_file.write_text(log_content)
    return log_file


@pytest.fixture
def sample_log_entries() -> list[LogEntry]:
    """Sample parsed log entries."""
    return [
        LogEntry(
            timestamp=datetime(2026, 3, 7, 10, 0, 0),
            level=LogLevel.INFO,
            thread="1",
            message="System started",
            raw="2026-03-07 10:00:00.000 [1] INFO System started",
        ),
        LogEntry(
            timestamp=datetime(2026, 3, 7, 10, 0, 1, 123000),
            level=LogLevel.DEBUG,
            thread="2",
            message="INVITE sip:100@localhost",
            raw="2026-03-07 10:00:01.123 [2] DEBUG INVITE sip:100@localhost",
        ),
        LogEntry(
            timestamp=datetime(2026, 3, 7, 10, 0, 3, 789000),
            level=LogLevel.ERROR,
            thread="3",
            message="Call failed: timeout",
            raw="2026-03-07 10:00:03.789 [3] ERROR Call failed: timeout",
        ),
    ]


@pytest.fixture
def log_parser(sample_log_file: Path) -> LogParser:
    """LogParser instance with sample log file."""
    return LogParser(str(sample_log_file), encoding="utf-8")


# ============================================================================
# MCP Server Fixtures
# ============================================================================

@pytest.fixture
def mock_fastmcp():
    """Mock FastMCP server."""
    with patch("src.FastMCP") as mock:
        instance = MagicMock()
        mock.return_value = instance
        instance.tool = MagicMock()
        yield instance


# ============================================================================
# Async Event Loop
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Environment Variable Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def clean_env():
    """Clean and restore environment variables."""
    original_env = os.environ.copy()
    # Set test-specific environment variables
    os.environ["DB_NAME"] = "test_3cxpbx"
    os.environ["DB_USER"] = "test_user"
    os.environ["DB_PASSWORD"] = "test_pass"
    os.environ["DB_USE_SOCKET"] = "false"
    os.environ["MCP_NAME"] = "test-3cx-debugging"
    os.environ["ENABLE_WRITES"] = "false"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================================
# Markers for test categorization
# ============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "asyncio: Async tests")
    config.addinivalue_line("markers", "database: Tests requiring database access")
    config.addinivalue_line("markers", "requires_backup: Tests requiring backup data")