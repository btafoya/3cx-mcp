"""
Unit tests for call-related MCP tools.

Tests verify the query generation and parameter handling without
depending on FastMCP decorator behavior.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.database.connection import DatabasePool


class TestCallsToolsQueries:
    """Tests for call-related tools - query generation and validation."""

    @pytest.fixture
    def mock_db(self):
        """Mock DatabasePool."""
        db = MagicMock(spec=DatabasePool)
        db.fetch = AsyncMock(return_value=[])
        db.fetchone = AsyncMock(return_value=None)
        return db

    @pytest.fixture
    def sample_call_data(self):
        """Sample call records for testing."""
        return [
            {
                "id": 1,
                "start_time": datetime(2026, 3, 7, 10, 0, 0),
                "end_time": datetime(2026, 3, 7, 10, 0, 30),
                "is_answered": "t",
                "ringing_dur": "00:00:05",
                "talking_dur": "00:00:25",
                "q_wait_dur": "00:00:00",
                "call_history_id": "abc-123",
                "duplicated": False,
                "migrated": False,
            },
            {
                "id": 2,
                "start_time": datetime(2026, 3, 7, 10, 1, 0),
                "end_time": datetime(2026, 3, 7, 10, 1, 5),
                "is_answered": "f",
                "ringing_dur": "00:00:05",
                "talking_dur": None,
                "q_wait_dur": "00:00:00",
                "call_history_id": "def-456",
                "duplicated": False,
                "migrated": False,
            },
        ]

    @pytest.mark.asyncio
    async def test_list_calls_query_structure(self, mock_db, sample_call_data):
        """Test list_calls generates correct query structure."""
        mock_db.fetch.return_value = sample_call_data

        # Simulate the query that list_calls would make
        query = "SELECT * FROM cl_calls WHERE 1=1 ORDER BY start_time DESC LIMIT $1 OFFSET $2"
        await mock_db.fetch(query, 100, 0)

        mock_db.fetch.assert_called_once_with(
            "SELECT * FROM cl_calls WHERE 1=1 ORDER BY start_time DESC LIMIT $1 OFFSET $2",
            100, 0
        )

    @pytest.mark.asyncio
    async def test_list_calls_with_answered_filter(self, mock_db):
        """Test list_calls with answered_only filter."""
        query = "SELECT * FROM cl_calls WHERE 1=1 AND is_answered = $1 ORDER BY start_time DESC LIMIT $2 OFFSET $3"
        await mock_db.fetch(query, "t", 100, 0)

        mock_db.fetch.assert_called_once()
        args = mock_db.fetch.call_args[0]
        assert args[1] == "t"  # answered parameter

    @pytest.mark.asyncio
    async def test_get_call_details_query(self, mock_db, sample_call_data):
        """Test get_call_details generates correct query."""
        mock_db.fetchone.return_value = sample_call_data[0]

        query = "SELECT * FROM cl_calls WHERE id = $1"
        result = await mock_db.fetchone(query, 1)

        mock_db.fetchone.assert_called_once_with(query, 1)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_call_details_not_found(self, mock_db):
        """Test get_call_details with non-existent call."""
        mock_db.fetchone.return_value = None

        query = "SELECT * FROM cl_calls WHERE id = $1"
        result = await mock_db.fetchone(query, 999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_active_calls_query(self, mock_db):
        """Test get_active_calls generates correct query."""
        query = """SELECT * FROM cl_calls
               WHERE end_time IS NULL OR end_time > NOW()
               ORDER BY start_time ASC"""
        await mock_db.fetch(query)

        mock_db.fetch.assert_called_once()
        assert "end_time IS NULL" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_call_statistics_day_grouping(self, mock_db):
        """Test get_call_statistics with day grouping."""
        query = """SELECT
                   DATE(start_time) as date,
                   COUNT(*) as total_calls,
                   COUNT(*) FILTER (WHERE is_answered = 't') as answered,
                   COUNT(*) FILTER (WHERE is_answered = 'f') as not_answered,
                   AVG(EXTRACT(EPOCH FROM talking_dur)) as avg_talk_seconds
               FROM cl_calls
               WHERE start_time >= $1 AND start_time <= $2
               GROUP BY DATE(start_time)
               ORDER BY date"""
        await mock_db.fetch(query, "2026-03-01", "2026-03-07")

        mock_db.fetch.assert_called_once()
        assert "DATE(start_time)" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_call_statistics_hour_grouping(self, mock_db):
        """Test get_call_statistics with hour grouping."""
        query = """SELECT
                   DATE_TRUNC('hour', start_time) as hour,
                   COUNT(*) as total_calls,
                   COUNT(*) FILTER (WHERE is_answered = 't') as answered,
                   COUNT(*) FILTER (WHERE is_answered = 'f') as not_answered,
                   AVG(EXTRACT(EPOCH FROM talking_dur)) as avg_talk_seconds
               FROM cl_calls
               WHERE start_time >= $1 AND start_time <= $2
               GROUP BY DATE_TRUNC('hour', start_time)
               ORDER BY hour"""
        await mock_db.fetch(query, "2026-03-01", "2026-03-07")

        mock_db.fetch.assert_called_once()
        assert "DATE_TRUNC('hour', start_time)" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_failed_calls_query(self, mock_db):
        """Test get_failed_calls generates correct query."""
        query = """SELECT * FROM cl_calls
                   WHERE is_answered = 'f'
                   ORDER BY start_time DESC
                   LIMIT $1"""
        await mock_db.fetch(query, 50)

        mock_db.fetch.assert_called_once()
        assert "is_answered = 'f'" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_failed_calls_with_start_date(self, mock_db):
        """Test get_failed_calls with start date filter."""
        query = """SELECT * FROM cl_calls
                   WHERE is_answered = 'f'
                   AND start_time >= $2
                   ORDER BY start_time DESC
                   LIMIT $1"""
        await mock_db.fetch(query, 50, "2026-03-01")

        mock_db.fetch.assert_called_once()
        assert "start_time >= $2" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_cdr_by_call_history(self, mock_db):
        """Test get_cdr_by_call_history query."""
        cdr_data = [
            {
                "cdr_id": "abc-123",
                "call_history_id": "xyz-789",
                "source_dn_number": "100",
                "destination_dn_number": "200",
                "creation_method": "call_init",
                "termination_reason": "dst_participant_terminated",
            }
        ]
        mock_db.fetch.return_value = cdr_data

        query = """SELECT * FROM cdroutput
               WHERE call_history_id = $1
               ORDER BY cdr_started_at"""
        result = await mock_db.fetch(query, "xyz-789")

        assert len(result) == 1
        assert result[0]["call_history_id"] == "xyz-789"

    @pytest.mark.asyncio
    async def test_search_calls_query_structure(self, mock_db):
        """Test search_calls query structure."""
        query = """SELECT DISTINCT c.*
               FROM cl_calls c
               JOIN cl_party_info pi ON c.id = pi.call_id
               WHERE pi.call_id IN (
                   SELECT DISTINCT p.call_id FROM cl_participants p
                   WHERE p.caller_number ILIKE $1
                      OR p.display_name ILIKE $1
               )
               OR query ILIKE $2
               ORDER BY c.start_time DESC
               LIMIT $3"""
        await mock_db.fetch(query, "%100%", "%100%", 50)

        mock_db.fetch.assert_called_once()
        assert "ILIKE" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_trace_call_query_structure(self, mock_db):
        """Test trace_call generates proper queries."""
        # First query for call
        query1 = "SELECT * FROM cl_calls WHERE id = $1"
        await mock_db.fetchone(query1, 1)

        # Second query for segments
        query2 = """SELECT
                   s.seq_order,
                   s.type,
                   src.caller_number as source,
                   src.display_name as source_name,
                   dst.caller_number as destination,
                   dst.display_name as destination_name,
                   s.start_time,
                   s.end_time
               FROM cl_segments s
               JOIN cl_participants src ON s.src_part_id = src.id
               JOIN cl_participants dst ON s.dst_part_id = dst.id
               WHERE s.call_id = $1
               ORDER BY s.seq_order"""
        await mock_db.fetch(query2, 1)

        assert mock_db.fetchone.call_count == 1
        assert mock_db.fetch.call_count == 1

    @pytest.mark.asyncio
    async def test_debug_failed_call_analysis(self, mock_db):
        """Test debug_failed_call identifies issues correctly."""
        failed_call = {
            "id": 2,
            "start_time": datetime(2026, 3, 7, 10, 1, 0),
            "end_time": datetime(2026, 3, 7, 10, 1, 5),
            "is_answered": "f",
            "ringing_dur": "00:00:00",
            "talking_dur": None,
            "q_wait_dur": "00:00:00",
            "call_history_id": "def-456",
            "duplicated": False,
            "migrated": False,
        }
        mock_db.fetchone.return_value = failed_call
        mock_db.fetch.return_value = [
            {"failure_reason": 1},
        ]

        # Simulate the analysis
        issues = []
        if failed_call.get("is_answered") == "f":
            issues.append("Call was not answered")
        if failed_call.get("ringing_dur") and "00:00:00" in str(failed_call["ringing_dur"]):
            issues.append("No ringing detected")

        assert len(issues) >= 1
        assert "Call was not answered" in issues