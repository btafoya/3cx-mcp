"""
Unit tests for database connection and query handling.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from src.config import DatabaseConfig
from src.database.connection import (
    DatabasePool,
    DatabaseError,
    ConnectionError,
    QueryError,
)


class TestDatabaseError:
    """Tests for DatabaseError exception."""

    def test_database_error_base(self):
        """Test DatabaseError base exception."""
        error = DatabaseError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


class TestConnectionError:
    """Tests for ConnectionError exception."""

    def test_connection_error(self):
        """Test ConnectionError exception."""
        error = ConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, DatabaseError)


class TestQueryError:
    """Tests for QueryError exception."""

    def test_query_error(self):
        """Test QueryError with cause."""
        cause = ValueError("Invalid SQL")
        error = QueryError("SELECT * FROM test", cause)
        assert "Query failed" in str(error)
        assert str(cause) in str(error)
        assert error.query == "SELECT * FROM test"
        assert error.cause == cause
        assert isinstance(error, DatabaseError)


class TestDatabasePool:
    """Tests for DatabasePool."""

    @pytest.fixture
    def db_config(self):
        """Test database configuration."""
        return DatabaseConfig(
            host="localhost",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass",
            use_socket=False,
            pool_size=3,
        )

    @pytest.fixture
    def db_pool(self, db_config):
        """DatabasePool instance for testing."""
        return DatabasePool(db_config)

    def test_db_pool_config(self, db_pool, db_config):
        """Test DatabasePool stores config."""
        assert db_pool.config == db_config
        assert db_pool._pool is None

    @pytest.mark.asyncio
    async def test_db_pool_execute(self, db_pool):
        """Test DatabasePool.execute()."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="INSERT 1")
        mock_pool.acquire().__aenter__.return_value = mock_conn
        mock_pool.acquire().__aexit__.return_value = None
        db_pool._pool = mock_pool

        result = await db_pool.execute("INSERT INTO test VALUES ($1)", "value")

        assert result == "INSERT 1"
        mock_conn.execute.assert_called_once_with("INSERT INTO test VALUES ($1)", "value")

    @pytest.mark.asyncio
    async def test_db_pool_execute_error(self, db_pool):
        """Test DatabasePool.execute() with error."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("SQL error"))
        mock_pool.acquire().__aenter__.return_value = mock_conn
        mock_pool.acquire().__aexit__.return_value = None
        db_pool._pool = mock_pool

        with pytest.raises(QueryError, match="Query failed"):
            await db_pool.execute("INVALID SQL")

    @pytest.mark.asyncio
    async def test_db_pool_fetch(self, db_pool):
        """Test DatabasePool.fetch()."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_rows = [
            {"id": 1, "name": "Test 1"},
            {"id": 2, "name": "Test 2"},
        ]
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_pool.acquire().__aenter__.return_value = mock_conn
        mock_pool.acquire().__aexit__.return_value = None
        db_pool._pool = mock_pool

        result = await db_pool.fetch("SELECT * FROM test")

        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "Test 1"}
        assert result[1] == {"id": 2, "name": "Test 2"}

    @pytest.mark.asyncio
    async def test_db_pool_fetch_empty(self, db_pool):
        """Test DatabasePool.fetch() with no results."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool.acquire().__aenter__.return_value = mock_conn
        mock_pool.acquire().__aexit__.return_value = None
        db_pool._pool = mock_pool

        result = await db_pool.fetch("SELECT * FROM test WHERE false")

        assert result == []

    @pytest.mark.asyncio
    async def test_db_pool_fetch_error(self, db_pool):
        """Test DatabasePool.fetch() with error."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=Exception("Connection lost"))
        mock_pool.acquire().__aenter__.return_value = mock_conn
        mock_pool.acquire().__aexit__.return_value = None
        db_pool._pool = mock_pool

        with pytest.raises(QueryError, match="Query failed"):
            await db_pool.fetch("SELECT * FROM test")

    @pytest.mark.asyncio
    async def test_db_pool_fetchone(self, db_pool):
        """Test DatabasePool.fetchone()."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_rows = [{"id": 1, "name": "Test 1"}]
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        mock_pool.acquire().__aenter__.return_value = mock_conn
        mock_pool.acquire().__aexit__.return_value = None
        db_pool._pool = mock_pool

        result = await db_pool.fetchone("SELECT * FROM test WHERE id = 1")

        assert result == {"id": 1, "name": "Test 1"}

    @pytest.mark.asyncio
    async def test_db_pool_fetchone_none(self, db_pool):
        """Test DatabasePool.fetchone() with no results."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_pool.acquire().__aenter__.return_value = mock_conn
        mock_pool.acquire().__aexit__.return_value = None
        db_pool._pool = mock_pool

        result = await db_pool.fetchone("SELECT * FROM test WHERE id = 999")

        assert result is None

    @pytest.mark.asyncio
    async def test_db_pool_fetchval(self, db_pool):
        """Test DatabasePool.fetchval()."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=42)
        mock_pool.acquire().__aenter__.return_value = mock_conn
        mock_pool.acquire().__aexit__.return_value = None
        db_pool._pool = mock_pool

        result = await db_pool.fetchval("SELECT COUNT(*) FROM test")

        assert result == 42

    @pytest.mark.asyncio
    async def test_db_pool_fetchval_error(self, db_pool):
        """Test DatabasePool.fetchval() with error."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=Exception("Table not found"))
        mock_pool.acquire().__aenter__.return_value = mock_conn
        mock_pool.acquire().__aexit__.return_value = None
        db_pool._pool = mock_pool

        with pytest.raises(QueryError, match="Query failed"):
            await db_pool.fetchval("SELECT * FROM nonexistent")

    @pytest.mark.asyncio
    async def test_db_pool_close(self, db_pool):
        """Test DatabasePool.close()."""
        mock_pool = MagicMock()
        mock_pool.close = AsyncMock()
        db_pool._pool = mock_pool

        await db_pool.close()

        mock_pool.close.assert_called_once()
        assert db_pool._pool is None

    @pytest.mark.asyncio
    async def test_db_pool_close_without_pool(self, db_pool):
        """Test DatabasePool.close() without initialized pool."""
        db_pool._pool = None

        # Should not raise
        await db_pool.close()

    @pytest.mark.asyncio
    async def test_db_pool_connection_context(self, db_pool):
        """Test DatabasePool.connection() context manager."""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_pool.acquire().__aenter__.return_value = mock_conn
        mock_pool.acquire().__aexit__.return_value = None
        db_pool._pool = mock_pool

        async with db_pool.connection() as conn:
            assert conn is mock_conn
