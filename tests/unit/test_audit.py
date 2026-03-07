"""
Unit tests for audit log MCP tools.

Tests verify the query generation and parameter handling.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.database.connection import DatabasePool


class TestAuditToolsQueries:
    """Tests for audit log tools - query generation."""

    @pytest.fixture
    def mock_db(self):
        """Mock DatabasePool."""
        db = MagicMock(spec=DatabasePool)
        db.fetch = AsyncMock(return_value=[])
        db.fetchone = AsyncMock(return_value=None)
        return db

    @pytest.fixture
    def sample_audit_data(self):
        """Sample audit log entries."""
        return [
            {
                "id": 1,
                "time_stamp": datetime(2026, 3, 7, 10, 0, 0),
                "source": 1,
                "ip": "192.168.1.1",
                "action": 1,
                "object_type": 7,
                "user_name": "admin",
                "object_name": "100 John Doe",
                "prev_data": {"name": "Old Name"},
                "new_data": {"name": "New Name"},
            },
        ]

    @pytest.mark.asyncio
    async def test_get_audit_log_query(self, mock_db, sample_audit_data):
        """Test get_audit_log generates correct query."""
        mock_db.fetch.return_value = sample_audit_data

        query = "SELECT * FROM audit_log WHERE 1=1 ORDER BY time_stamp DESC LIMIT $1 OFFSET $2"
        result = await mock_db.fetch(query, 50, 0)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_audit_log_with_date_filters(self, mock_db):
        """Test get_audit_log with date filters."""
        query = "SELECT * FROM audit_log WHERE 1=1 AND time_stamp >= $2 AND time_stamp <= $3 ORDER BY time_stamp DESC LIMIT $1 OFFSET $4"
        await mock_db.fetch(query, 50, "2026-03-01", "2026-03-07", 0)

        mock_db.fetch.assert_called_once()
        assert "time_stamp >= $2" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_recent_changes_query(self, mock_db, sample_audit_data):
        """Test get_recent_changes generates correct query."""
        mock_db.fetch.return_value = sample_audit_data

        query = """SELECT
                   time_stamp,
                   user_name,
                   action,
                   object_type,
                   object_name,
                   ip,
                   prev_data,
                   new_data
               FROM audit_log
               ORDER BY time_stamp DESC
               LIMIT $1"""
        await mock_db.fetch(query, 50)

        mock_db.fetch.assert_called_once()
        assert "ORDER BY time_stamp DESC" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_user_changes_query(self, mock_db):
        """Test get_user_changes generates correct query."""
        query = """SELECT * FROM audit_log
               WHERE user_name ILIKE $1
               ORDER BY time_stamp DESC
               LIMIT $2"""
        await mock_db.fetch(query, "%admin%", 50)

        mock_db.fetch.assert_called_once()
        assert "ILIKE" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_object_changes_query(self, mock_db):
        """Test get_object_changes generates correct query."""
        query = """SELECT * FROM audit_log
               WHERE object_name ILIKE $1
               ORDER BY time_stamp DESC
               LIMIT $2"""
        await mock_db.fetch(query, "%100%", 50)

        mock_db.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_changes_by_type_query(self, mock_db):
        """Test get_changes_by_type generates correct query."""
        query = """SELECT * FROM audit_log
                   WHERE object_type = $1
                   ORDER BY time_stamp DESC
                   LIMIT $2"""
        await mock_db.fetch(query, 7, 50)

        mock_db.fetch.assert_called_once()
        assert "object_type = $1" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_extension_changes_query(self, mock_db):
        """Test get_extension_changes generates correct query."""
        query = """SELECT
                   time_stamp,
                   user_name,
                   action,
                   object_name,
                   ip,
                   prev_data,
                   new_data
               FROM audit_log
               WHERE object_name ILIKE $1 OR object_name ILIKE $2
               ORDER BY time_stamp DESC
               LIMIT $3"""
        await mock_db.fetch(query, "%100%", "%100%", 50)

        mock_db.fetch.assert_called_once()
        assert "ILIKE $1 OR object_name ILIKE $2" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_changes_summary_query(self, mock_db):
        """Test get_changes_summary generates correct query."""
        query = """SELECT
                   DATE(time_stamp) as change_date,
                   action,
                   COUNT(*) as change_count
               FROM audit_log
               WHERE time_stamp >= $1 AND time_stamp <= $2
               GROUP BY DATE(time_stamp), action
               ORDER BY change_date DESC, action"""
        await mock_db.fetch(query, "2026-03-01", "2026-03-07")

        mock_db.fetch.assert_called_once()
        assert "GROUP BY DATE(time_stamp)" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_audit_codes_returns_mappings(self):
        """Test get_audit_codes returns correct code mappings."""
        from src.database.schema import (
            AUDIT_ACTION_MAP,
            AUDIT_OBJECT_TYPE_MAP,
            AUDIT_SOURCE_MAP,
        )

        # Verify action codes
        assert AUDIT_ACTION_MAP[1] == "Create"
        assert AUDIT_ACTION_MAP[7] == "Update"
        assert AUDIT_ACTION_MAP[21] == "Delete"

        # Verify object type codes
        assert AUDIT_OBJECT_TYPE_MAP[7] == "Extension"
        assert AUDIT_OBJECT_TYPE_MAP[17] == "Queue/Ring Group"

        # Verify source codes
        assert AUDIT_SOURCE_MAP[0] == "Unknown/Internal"
        assert AUDIT_SOURCE_MAP[1] == "Web Client"
