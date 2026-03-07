"""
Call-related MCP tools.

Provides call record queries and combined database+log operations.
"""
from mcp.server.fastmcp import FastMCP
from ..database.connection import DatabasePool


def register(mcp: FastMCP, db: DatabasePool):
    """Register call tools."""

    @mcp.tool()
    async def list_calls(
        limit: int = 100,
        offset: int = 0,
        answered_only: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """List call records with filtering.

        Args:
            limit: Maximum records to return (default: 100)
            offset: Records to skip for pagination
            answered_only: Filter by answered status only
            start_date: Start date filter (ISO format)
            end_date: End date filter (ISO format)

        Returns:
            List of call records with metadata.
        """
        query = "SELECT * FROM cl_calls WHERE 1=1"
        params = []

        if answered_only is not None:
            query += " AND is_answered = $1"
            params.append("t" if answered_only else "f")

        if start_date:
            query += f" AND start_time >= ${len(params) + 1}"
            params.append(start_date)

        if end_date:
            query += f" AND start_time <= ${len(params) + 1}"
            params.append(end_date)

        query += f" ORDER BY start_time DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        params.extend([limit, offset])

        return await db.fetch(query, *params)

    @mcp.tool()
    async def get_call_details(call_id: int) -> dict | None:
        """Get full details of a specific call.

        Args:
            call_id: The call ID (integer from cl_calls.id)

        Returns:
            Complete call record or None if not found.
        """
        return await db.fetchone(
            "SELECT * FROM cl_calls WHERE id = $1",
            call_id
        )

    @mcp.tool()
    async def get_active_calls() -> list[dict]:
        """Get all currently active calls.

        Returns:
            List of active calls with current state.
        """
        return await db.fetch(
            """SELECT * FROM cl_calls
               WHERE end_time IS NULL OR end_time > NOW()
               ORDER BY start_time ASC"""
        )

    @mcp.tool()
    async def get_call_flow(call_id: int) -> dict:
        """Get complete call flow path.

        Args:
            call_id: The call ID

        Returns:
            Call flow with participants and segments.
        """
        call = await db.fetchone(
            "SELECT * FROM cl_calls WHERE id = $1",
            call_id
        )

        if not call:
            return None

        # Get call segments with participant details
        segments = await db.fetch(
            """SELECT
                   s.seq_order,
                   s.type as segment_type,
                   s.start_time,
                   s.end_time,
                   src.caller_number as source,
                   src.display_name as source_name,
                   dst.caller_number as destination,
                   dst.display_name as destination_name
               FROM cl_segments s
               JOIN cl_participants src ON s.src_part_id = src.id
               JOIN cl_participants dst ON s.dst_part_id = dst.id
               WHERE s.call_id = $1
               ORDER BY s.seq_order""",
            call_id
        )

        # Get party info
        party_info = await db.fetch(
            "SELECT * FROM cl_party_info WHERE call_id = $1",
            call_id
        )

        return {
            "call": call,
            "segments": segments,
            "party_info": party_info
        }

    @mcp.tool()
    async def get_call_statistics(
        start_date: str,
        end_date: str,
        group_by: str = "day",
    ) -> list[dict]:
        """Get call statistics for a date range.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            group_by: Grouping level (day, hour)

        Returns:
            Aggregated statistics with volume, duration, success rates.
        """
        if group_by == "day":
            query = """
                SELECT
                    DATE(start_time) as date,
                    COUNT(*) as total_calls,
                    COUNT(*) FILTER (WHERE is_answered = 't') as answered,
                    COUNT(*) FILTER (WHERE is_answered = 'f') as not_answered,
                    AVG(EXTRACT(EPOCH FROM talking_dur)) as avg_talk_seconds
                FROM cl_calls
                WHERE start_time >= $1 AND start_time <= $2
                GROUP BY DATE(start_time)
                ORDER BY date
            """
        elif group_by == "hour":
            query = """
                SELECT
                    DATE_TRUNC('hour', start_time) as hour,
                    COUNT(*) as total_calls,
                    COUNT(*) FILTER (WHERE is_answered = 't') as answered,
                    COUNT(*) FILTER (WHERE is_answered = 'f') as not_answered,
                    AVG(EXTRACT(EPOCH FROM talking_dur)) as avg_talk_seconds
                FROM cl_calls
                WHERE start_time >= $1 AND start_time <= $2
                GROUP BY DATE_TRUNC('hour', start_time)
                ORDER BY hour
            """
        else:
            raise ValueError(f"Invalid group_by: {group_by}")

        return await db.fetch(query, start_date, end_date)

    @mcp.tool()
    async def search_calls(query: str, limit: int = 50) -> list[dict]:
        """Search call records by participant info.

        Args:
            query: Search term (caller, extension)
            limit: Maximum results to return

        Returns:
            Matching call records.
        """
        search_pattern = f"%{query}%"
        return await db.fetch(
            """SELECT DISTINCT c.*
               FROM cl_calls c
               JOIN cl_party_info pi ON c.id = pi.call_id
               WHERE pi.call_id IN (
                   SELECT DISTINCT p.call_id FROM cl_participants p
                   WHERE p.caller_number ILIKE $1
                      OR p.display_name ILIKE $1
               )
               OR query ILIKE $2
               ORDER BY c.start_time DESC
               LIMIT $3""",
            search_pattern, search_pattern, limit
        )

    @mcp.tool()
    async def trace_call(call_id: int) -> dict:
        """Get complete call trace combining database and logs.

        Args:
            call_id: The call ID (integer)

        Returns:
            Combined call record, flow segments, and log entries.
        """
        # Get call record
        call = await db.fetchone(
            "SELECT * FROM cl_calls WHERE id = $1",
            call_id
        )

        if not call:
            return None

        # Get call flow segments
        segments = await db.fetch(
            """SELECT
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
               ORDER BY s.seq_order""",
            call_id
        )

        return {
            "call": call,
            "segments": segments
        }

    @mcp.tool()
    async def debug_failed_call(call_id: int) -> dict:
        """Debug a failed call to identify root cause.

        Args:
            call_id: The call ID

        Returns:
            Analysis with segments, party info, and potential issues.
        """
        # Get call details
        call = await db.fetchone(
            "SELECT * FROM cl_calls WHERE id = $1",
            call_id
        )

        if not call:
            return None

        # Get party info for analysis
        party_info = await db.fetch(
            "SELECT * FROM cl_party_info WHERE call_id = $1",
            call_id
        )

        # Get segments to see routing path
        segments = await db.fetch(
            """SELECT
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
               ORDER BY s.seq_order""",
            call_id
        )

        # Analyze potential issues
        issues = []

        if call.get("is_answered") == "f":
            issues.append("Call was not answered")

        if call.get("talking_dur") and "00:00:00" in str(call["talking_dur"]):
            issues.append("Zero talk time")

        if call.get("ringing_dur") and "00:00:00" in str(call["ringing_dur"]):
            issues.append("No ringing detected")

        # Check party info for failure reasons
        for pi in party_info:
            if pi.get("failure_reason"):
                issues.append(f"Party failure reason: {pi['failure_reason']}")

        return {
            "call": call,
            "party_info": party_info,
            "segments": segments,
            "issues": issues
        }

    @mcp.tool()
    async def get_failed_calls(
        limit: int = 50,
        start_date: str | None = None,
    ) -> list[dict]:
        """Get list of failed calls.

        Args:
            limit: Maximum records to return
            start_date: Optional start date filter

        Returns:
            List of failed call records.
        """
        query = """SELECT * FROM cl_calls
                   WHERE is_answered = 'f'
                   ORDER BY start_time DESC
                   LIMIT $1"""
        params = [limit]

        if start_date:
            query = query.replace("ORDER BY", f"AND start_time >= $2 ORDER BY")
            params.append(start_date)

        return await db.fetch(query, *params)

    @mcp.tool()
    async def get_cdr_by_call_history(call_history_id: str) -> list[dict]:
        """Get CDR entries for a call history ID.

        Args:
            call_history_id: The call history UUID

        Returns:
            List of CDR entries showing the complete routing path.
        """
        return await db.fetch(
            """SELECT * FROM cdroutput
               WHERE call_history_id = $1
               ORDER BY cdr_started_at""",
            call_history_id
        )