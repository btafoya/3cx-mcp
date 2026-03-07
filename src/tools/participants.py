"""
Extension/participant management MCP tools.

Note: 3CX Professional does not have a separate extensions table.
Extension information is stored in cl_participants table.
"""
from mcp.server.fastmcp import FastMCP
from ..database.connection import DatabasePool
from ..database.schema import DN_TYPE_MAP


def register(mcp: FastMCP, db: DatabasePool):
    """Register participant tools."""

    @mcp.tool()
    async def list_participants(
        limit: int = 100,
        offset: int = 0,
        dn_type: int | None = None,
    ) -> list[dict]:
        """List all participants (extensions, trunks, queues).

        Args:
            limit: Maximum records to return
            offset: Records to skip for pagination
            dn_type: Filter by DN type (0=extension, 1=external, 2=ring_group, 5=voicemail)

        Returns:
            List of participants.
        """
        query = "SELECT * FROM cl_participants WHERE 1=1"
        params = []

        if dn_type is not None:
            query += " AND dn_type = $1"
            params.append(dn_type)

        query += f" ORDER BY id LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        params.extend([limit, offset])

        return await db.fetch(query, *params)

    @mcp.tool()
    async def get_participant(participant_id: int) -> dict | None:
        """Get details of a specific participant.

        Args:
            participant_id: The participant ID from cl_participants

        Returns:
            Participant details or None if not found.
        """
        return await db.fetchone(
            "SELECT * FROM cl_participants WHERE id = $1",
            participant_id
        )

    @mcp.tool()
    async def get_extensions_only() -> list[dict]:
        """Get list of extensions only (dn_type = 0).

        Returns:
            List of extensions with their DN numbers.
        """
        return await db.fetch(
            """SELECT * FROM cl_participants
               WHERE dn_type = 0
               ORDER BY dn"""
        )

    @mcp.tool()
    async def get_queues() -> list[dict]:
        """Get list of ring groups/queues.

        Returns:
            List of queues with their DN numbers.
        """
        return await db.fetch(
            """SELECT * FROM cl_participants
               WHERE dn_type = 2
               ORDER BY dn"""
        )

    @mcp.tool()
    async def get_participant_by_dn(dn: str, dn_type: int | None = None) -> dict | None:
        """Get participant by DN number.

        Args:
            dn: DN number
            dn_type: Optional DN type filter

        Returns:
            Participant details or None if not found.
        """
        if dn_type is not None:
            return await db.fetchone(
                "SELECT * FROM cl_participants WHERE dn = $1 AND dn_type = $2",
                dn, dn_type
            )
        return await db.fetchone(
            "SELECT * FROM cl_participants WHERE dn = $1",
            dn
        )

    @mcp.tool()
    async def search_participants(query: str, limit: int = 50) -> list[dict]:
        """Search participants by display name or caller number.

        Args:
            query: Search term
            limit: Maximum results to return

        Returns:
            Matching participants.
        """
        search_pattern = f"%{query}%"
        return await db.fetch(
            """SELECT * FROM cl_participants
               WHERE display_name ILIKE $1
                  OR caller_number ILIKE $1
                  OR firstlastname ILIKE $1
               ORDER BY display_name
               LIMIT $2""",
            search_pattern, limit
        )

    @mcp.tool()
    async def get_external_lines() -> list[dict]:
        """Get list of external lines/trunks (dn_type = 1).

        Returns:
            List of external lines.
        """
        return await db.fetch(
            """SELECT * FROM cl_participants
               WHERE dn_type = 1
               ORDER BY dn"""
        )

    @mcp.tool()
    async def get_voicemails() -> list[dict]:
        """Get list of voicemail boxes (dn_type = 5).

        Returns:
            List of voicemail boxes.
        """
        return await db.fetch(
            """SELECT * FROM cl_participants
               WHERE dn_type = 5
               ORDER BY dn"""
        )

    @mcp.tool()
    async def get_participant_stats(participant_id: int) -> dict:
        """Get statistics for a participant.

        Args:
            participant_id: The participant ID

        Returns:
            Statistics including call counts, duration, etc.
        """
        # Get calls involving this participant
        calls = await db.fetch(
            """SELECT
                   COUNT(*) as total_calls,
                   COUNT(*) FILTER (WHERE is_answered = 't') as answered,
                   COUNT(*) FILTER (WHERE is_answered = 'f') as not_answered,
                   SUM(EXTRACT(EPOCH FROM talking_dur)) as total_talk_seconds
               FROM cl_party_info pi
               JOIN cl_calls c ON pi.call_id = c.id
               WHERE pi.party_id = $1""",
            participant_id
        )
        return calls[0] if calls else {}

    @mcp.tool()
    async def list_dn_types() -> list[dict]:
        """Get list of DN types with descriptions.

        Returns:
            List of DN types.
        """
        return [
            {"code": code, "name": name}
            for code, name in DN_TYPE_MAP.items()
        ]