"""
Queue/ring group MCP tools.

Provides queue statistics and call center analytics.
"""
from mcp.server.fastmcp import FastMCP
from ..database.connection import DatabasePool


def register(mcp: FastMCP, db: DatabasePool):
    """Register queue tools."""

    @mcp.tool()
    async def list_queues() -> list[dict]:
        """List all call queues/ring groups.

        Returns:
            List of queues from cl_participants where dn_type=2.
        """
        return await db.fetch(
            """SELECT * FROM cl_participants
               WHERE dn_type = 2
               ORDER BY dn"""
        )

    @mcp.tool()
    async def get_queue_stats(queue_dn: str, days: int = 7) -> dict:
        """Get queue statistics for a time period.

        Args:
            queue_dn: Queue DN number
            days: Number of days to analyze

        Returns:
            Queue statistics with volume, wait times, abandon rates.
        """
        return await db.fetchone(
            """SELECT
                   COUNT(*) as total_calls,
                   COUNT(*) FILTER (WHERE call_result = 'ANSWERED') as answered,
                   COUNT(*) FILTER (WHERE call_result = 'ABANDONED') as abandoned,
                   COUNT(*) FILTER (WHERE call_result = 'TIMEOUT') as timeout,
                   COUNT(*) FILTER (WHERE call_result = 'WP') as in_progress,
                   AVG(EXTRACT(EPOCH FROM ts_waiting)) as avg_wait_seconds
               FROM callcent_queuecalls
               WHERE q_num = $1
                 AND time_start >= NOW() - INTERVAL '1 day' * $2""",
            queue_dn, days
        )

    @mcp.tool()
    async def get_queue_abandoned_calls(queue_dn: str, limit: int = 50) -> list[dict]:
        """Get abandoned calls for a queue.

        Args:
            queue_dn: Queue DN number
            limit: Maximum records to return

        Returns:
            Abandoned calls with wait times and reasons.
        """
        return await db.fetch(
            """SELECT * FROM callcent_queuecalls
               WHERE q_num = $1
                 AND call_result = 'ABANDONED'
               ORDER BY time_start DESC
               LIMIT $2""",
            queue_dn, limit
        )

    @mcp.tool()
    async def get_all_queues_stats(days: int = 7) -> list[dict]:
        """Get statistics for all queues.

        Args:
            days: Number of days to analyze

        Returns:
            Statistics for each queue.
        """
        return await db.fetch(
            """SELECT
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
               ORDER BY total_calls DESC""",
            days
        )

    @mcp.tool()
    async def get_queue_calls(
        queue_dn: str,
        start_date: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get all calls for a queue.

        Args:
            queue_dn: Queue DN number
            start_date: Optional start date filter
            limit: Maximum records to return

        Returns:
            Queue call records.
        """
        if start_date:
            return await db.fetch(
                """SELECT * FROM callcent_queuecalls
                   WHERE q_num = $1
                     AND time_start >= $2
                   ORDER BY time_start DESC
                   LIMIT $3""",
                queue_dn, start_date, limit
            )
        return await db.fetch(
            """SELECT * FROM callcent_queuecalls
               WHERE q_num = $1
               ORDER BY time_start DESC
               LIMIT $2""",
            queue_dn, limit
        )

    @mcp.tool()
    async def get_call_center_summary(days: int = 7) -> dict:
        """Get overall call center statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Overall call center metrics.
        """
        result = await db.fetchone(
            """SELECT
                   COUNT(*) as total_queue_calls,
                   COUNT(*) FILTER (WHERE call_result = 'ANSWERED') as answered,
                   COUNT(*) FILTER (WHERE call_result = 'ABANDONED') as abandoned,
                   COUNT(*) FILTER (WHERE call_result = 'TIMEOUT') as timeout,
                   AVG(EXTRACT(EPOCH FROM ts_waiting)) as avg_wait_seconds,
                   AVG(EXTRACT(EPOCH FROM ts_servicing)) as avg_service_seconds
               FROM callcent_queuecalls
               WHERE time_start >= NOW() - INTERVAL '1 day' * $1""",
            days
        )

        # Get unique queues with activity
        queues = await db.fetch(
            """SELECT COUNT(DISTINCT q_num) as active_queues
               FROM callcent_queuecalls
               WHERE time_start >= NOW() - INTERVAL '1 day' * $1""",
            days
        )

        if queues:
            result["active_queues"] = queues[0]["active_queues"]

        return result