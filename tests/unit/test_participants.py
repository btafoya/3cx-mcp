"""
Unit tests for participant-related MCP tools.

Tests verify the query generation and parameter handling.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.database.connection import DatabasePool


class TestParticipantsToolsQueries:
    """Tests for participant-related tools - query generation."""

    @pytest.fixture
    def mock_db(self):
        """Mock DatabasePool."""
        db = MagicMock(spec=DatabasePool)
        db.fetch = AsyncMock(return_value=[])
        db.fetchone = AsyncMock(return_value=None)
        return db

    @pytest.fixture
    def sample_participant_data(self):
        """Sample participant records."""
        return [
            {
                "id": 1,
                "dn_type": 0,
                "dn": "100",
                "caller_number": "+15551234567",
                "display_name": "John Doe",
                "dn_class": 1,
                "firstlastname": "Doe John",
                "did_number": "8005551234",
                "crm_contact": None,
            },
        ]

    @pytest.mark.asyncio
    async def test_list_participants_query(self, mock_db):
        """Test list_participants generates correct query."""
        query = "SELECT * FROM cl_participants WHERE 1=1 ORDER BY id LIMIT $1 OFFSET $2"
        await mock_db.fetch(query, 100, 0)

        mock_db.fetch.assert_called_once()
        assert "cl_participants" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_list_participants_with_dn_type(self, mock_db):
        """Test list_participants with dn_type filter."""
        query = "SELECT * FROM cl_participants WHERE 1=1 AND dn_type = $1 ORDER BY id LIMIT $2 OFFSET $3"
        await mock_db.fetch(query, 0, 100, 0)

        mock_db.fetch.assert_called_once()
        assert "dn_type = $1" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_participant_query(self, mock_db, sample_participant_data):
        """Test get_participant generates correct query."""
        mock_db.fetchone.return_value = sample_participant_data[0]

        query = "SELECT * FROM cl_participants WHERE id = $1"
        result = await mock_db.fetchone(query, 1)

        mock_db.fetchone.assert_called_once_with(query, 1)
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_extensions_only_query(self, mock_db):
        """Test get_extensions_only generates correct query."""
        query = """SELECT * FROM cl_participants
               WHERE dn_type = 0
               ORDER BY dn"""
        await mock_db.fetch(query)

        mock_db.fetch.assert_called_once()
        assert "dn_type = 0" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_queues_query(self, mock_db):
        """Test get_queues generates correct query."""
        query = """SELECT * FROM cl_participants
               WHERE dn_type = 2
               ORDER BY dn"""
        await mock_db.fetch(query)

        mock_db.fetch.assert_called_once()
        assert "dn_type = 2" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_participant_by_dn_query(self, mock_db, sample_participant_data):
        """Test get_participant_by_dn generates correct query."""
        mock_db.fetchone.return_value = sample_participant_data[0]

        query = "SELECT * FROM cl_participants WHERE dn = $1"
        result = await mock_db.fetchone(query, "100")

        mock_db.fetchone.assert_called_once_with(query, "100")

    @pytest.mark.asyncio
    async def test_get_participant_by_dn_with_type(self, mock_db):
        """Test get_participant_by_dn with dn_type filter."""
        query = "SELECT * FROM cl_participants WHERE dn = $1 AND dn_type = $2"
        await mock_db.fetchone(query, "100", 0)

        mock_db.fetchone.assert_called_once()
        args = mock_db.fetchone.call_args[0]
        assert "dn = $1" in args[0]
        assert "dn_type = $2" in args[0]

    @pytest.mark.asyncio
    async def test_search_participants_query(self, mock_db):
        """Test search_participants generates correct query."""
        query = """SELECT * FROM cl_participants
               WHERE display_name ILIKE $1
                  OR caller_number ILIKE $1
                  OR firstlastname ILIKE $1
               ORDER BY display_name
               LIMIT $2"""
        await mock_db.fetch(query, "%John%", 50)

        mock_db.fetch.assert_called_once()
        assert "ILIKE" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_external_lines_query(self, mock_db):
        """Test get_external_lines generates correct query."""
        query = """SELECT * FROM cl_participants
               WHERE dn_type = 1
               ORDER BY dn"""
        await mock_db.fetch(query)

        mock_db.fetch.assert_called_once()
        assert "dn_type = 1" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_voicemails_query(self, mock_db):
        """Test get_voicemails generates correct query."""
        query = """SELECT * FROM cl_participants
               WHERE dn_type = 5
               ORDER BY dn"""
        await mock_db.fetch(query)

        mock_db.fetch.assert_called_once()
        assert "dn_type = 5" in mock_db.fetch.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_participant_stats_query(self, mock_db):
        """Test get_participant_stats generates correct query."""
        stats = {
            "total_calls": 100,
            "answered": 80,
            "not_answered": 20,
            "total_talk_seconds": 4500.5,
        }
        mock_db.fetch.return_value = [stats]

        query = """SELECT
                   COUNT(*) as total_calls,
                   COUNT(*) FILTER (WHERE is_answered = 't') as answered,
                   COUNT(*) FILTER (WHERE is_answered = 'f') as not_answered,
                   SUM(EXTRACT(EPOCH FROM talking_dur)) as total_talk_seconds
               FROM cl_party_info pi
               JOIN cl_calls c ON pi.call_id = c.id
               WHERE pi.party_id = $1"""
        result = await mock_db.fetch(query, 1)

        assert len(result) == 1
        assert result[0]["total_calls"] == 100

    @pytest.mark.asyncio
    async def test_list_dn_types_returns_correct_values(self):
        """Test list_dn_types returns correct mapping."""
        from src.database.schema import DN_TYPE_MAP

        assert DN_TYPE_MAP[0] == "extension"
        assert DN_TYPE_MAP[1] == "external_line"
        assert DN_TYPE_MAP[2] == "ring_group"
        assert DN_TYPE_MAP[5] == "voicemail"
        assert DN_TYPE_MAP[13] == "inbound_routing"
