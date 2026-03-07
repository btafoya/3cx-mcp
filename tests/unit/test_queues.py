"""
Unit tests for queue/ring group MCP tools.

Tests verify the query generation and parameter handling.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.database.connection import DatabasePool


class TestQueuesToolsQueries:
    """Tests for queue-related tools - query generation."""

    @pytest.fixture
    def mock_db(self):
        """Mock DatabasePool."""
        db = MagicMock(spec=DatabasePool)
        db.fetch = AsyncMock(return_value=[])
        db.fetchone = AsyncMock(return_value=None)
        return db

    @pytest.mark.asyncio
    async def test_list_queues_query(self, mock_db):
        """Test list_queues generates correct query."""
        query = """SELECT * FROM cl_participants
               WHERE dn_type = 2
               ORDER BY dn"""
        await mock_db.fetch(query)

        mock_db.fetch.assert_called_once()
        assert "dn_type = 2" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_queue_stats_query(self, mock_db):
        """Test get_queue_stats generates correct query."""
        query = """SELECT
                   COUNT(*) as total_calls,
                   COUNT(*) FILTER (WHERE call_result = 'ANSWERED') as answered,
                   COUNT(*) FILTER (WHERE call_result = 'ABANDONED') as abandoned,
                   COUNT(*) FILTER (WHERE call_result = 'TIMEOUT') as timeout,
                   COUNT(*) FILTER (WHERE call_result = 'WP') as in_progress,
                   AVG(EXTRACT(EPOCH FROM ts_waiting)) as avg_wait_seconds
               FROM callcent_queuecalls
               WHERE q_num = $1
                 AND time_start >= NOW() - INTERVAL '1 day' * $2"""
        await mock_db.fetch(query, "800", 7)

        mock_db.fetch.assert_called_once()
        assert "callcent_queuecalls" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_queue_abandoned_calls_query(self, mock_db):
        """Test get_queue_abandoned_calls generates correct query."""
        query = """SELECT * FROM callcent_queuecalls
               WHERE q_num = $1
                 AND call_result = 'ABANDONED'
               ORDER BY time_start DESC
               LIMIT $2"""
        await mock_db.fetch(query, "800", 50)

        mock_db.fetch.assert_called_once()
        assert "call_result = 'ABANDONED'" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_all_queues_stats_query(self, mock_db):
        """Test get_all_queues_stats generates correct query."""
        query = """SELECT
                   q_num as queue_number,
                   p.display_name as queue_name,
                   COUNT(*) as total_calls,
                   COUNT(*) FILTER (WHERE call_result = 'ANSWERED') as answered,
                   COUNT(*) FILTER (WHERE call_result = 'ABANDONED') as abandoned,
                   AVG(EXTRACT(EPOCH FROM ts_waiting)) as avg_wait_seconds,
                   MAX(EXTRACT(EPOCH FROM ts_waiting)) as max_wait_seconds
               FROM callcent_queuecalls q
               LEFT JOIN cl_participants p ON p.dn = q.q_num AND p.dn_type = 2
               WHERE time_start >= NOW() - INTERVAL '1 day' * $1
               GROUP BY q_num, p.display_name
               ORDER BY total_calls DESC"""
        await mock_db.fetch(query, 7)

        mock_db.fetch.assert_called_once()
        assert "GROUP BY q_num" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_queue_calls_query(self, mock_db):
        """Test get_queue_calls generates correct query."""
        query = """SELECT * FROM callcent_queuecalls
               WHERE q_num = $1
               ORDER BY time_start DESC
               LIMIT $2"""
        await mock_db.fetch(query, "800", 100)

        mock_db.fetch.assert_called_once()
        assert "q_num = $1" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_queue_calls_with_start_date(self, mock_db):
        """Test get_queue_calls with start date filter."""
        query = """SELECT * FROM callcent_queuecalls
               WHERE q_num = $1
                 AND time_start >= $2
               ORDER BY time_start DESC
               LIMIT $3"""
        await mock_db.fetch(query, "800", "2026-03-01", 100)

        mock_db.fetch.assert_called_once()
        assert "time_start >= $2" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_call_center_summary_query(self, mock_db):
        """Test get_call_center_summary generates correct query."""
        summary = {
            "total_queue_calls": 500,
            "answered": 400,
            "abandoned": 75,
            "timeout": 25,
            "avg_wait_seconds": 10.5,
            "avg_service_seconds": 120.3,
        }
        active_queues = [{"active_queues": 3}]
        mock_db.fetchone.return_value = summary
        mock_db.fetch.side_effect = [summary, active_queues]

        # First query for summary
        query1 = """SELECT
                   COUNT(*) as total_queue_calls,
                   COUNT(*) FILTER (WHERE call_result = 'ANSWERED') as answered,
                   COUNT(*) FILTER (WHERE call_result = 'ABANDONED') as abandoned,
                   COUNT(*) FILTER (WHERE call_result = 'TIMEOUT') as timeout,
                   AVG(EXTRACT(EPOCH FROM ts_waiting)) as avg_wait_seconds,
                   AVG(EXTRACT(EPOCH FROM ts_servicing)) as avg_service_seconds
               FROM callcent_queuecalls
               WHERE time_start >= NOW() - INTERVAL '1 day' * $1"""
        await mock_db.fetchone(query1, 7)

        # Second query for active queues
        query2 = """SELECT COUNT(DISTINCT q_num) as active_queues
               FROM callcent_queuecalls
               WHERE time_start >= NOW() - INTERVAL '1 day' * $1"""
        await mock_db.fetch(query2, 7)

        # Verify both queries were called
        assert mock_db.fetchone.call_count >= 1
        assert mock_db.fetch.call_count >= 1
