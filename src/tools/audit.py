"""
Audit log MCP tools.

Provides access to 3CX configuration change audit trail.
"""
from mcp.server.fastmcp import FastMCP
from ..database.connection import DatabasePool
from ..database.schema import (
    AUDIT_ACTION_MAP,
    AUDIT_OBJECT_TYPE_MAP,
    AUDIT_SOURCE_MAP,
)


def register(mcp: FastMCP, db: DatabasePool):
    """Register audit tools."""

    @mcp.tool()
    async def get_audit_log(
        limit: int = 50,
        offset: int = 0,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """Get audit log entries with filtering.

        Args:
            limit: Maximum records to return
            offset: Records to skip for pagination
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Audit log entries.
        """
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if start_date:
            query += f" AND time_stamp >= ${len(params) + 1}"
            params.append(start_date)

        if end_date:
            query += f" AND time_stamp <= ${len(params) + 1}"
            params.append(end_date)

        query += f" ORDER BY time_stamp DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        params.extend([limit, offset])

        return await db.fetch(query, *params)

    @mcp.tool()
    async def get_recent_changes(limit: int = 50) -> list[dict]:
        """Get recent configuration changes.

        Args:
            limit: Maximum records to return

        Returns:
            Recent audit log entries.
        """
        return await db.fetch(
            """SELECT
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
               LIMIT $1""",
            limit
        )

    @mcp.tool()
    async def get_user_changes(user_name: str, limit: int = 50) -> list[dict]:
        """Get changes made by a specific user.

        Args:
            user_name: User name to filter by
            limit: Maximum records to return

        Returns:
            Audit log entries for the user.
        """
        return await db.fetch(
            """SELECT * FROM audit_log
               WHERE user_name ILIKE $1
               ORDER BY time_stamp DESC
               LIMIT $2""",
            f"%{user_name}%", limit
        )

    @mcp.tool()
    async def get_object_changes(object_name: str, limit: int = 50) -> list[dict]:
        """Get changes for a specific object.

        Args:
            object_name: Object name to filter by
            limit: Maximum records to return

        Returns:
            Audit log entries for the object.
        """
        return await db.fetch(
            """SELECT * FROM audit_log
               WHERE object_name ILIKE $1
               ORDER BY time_stamp DESC
               LIMIT $2""",
            f"%{object_name}%", limit
        )

    @mcp.tool()
    async def get_changes_by_type(
        object_type: int,
        limit: int = 50,
        start_date: str | None = None,
    ) -> list[dict]:
        """Get changes for a specific object type.

        Args:
            object_type: Object type code (7=Extension, 17=Queue, 25=IVR)
            limit: Maximum records to return
            start_date: Optional start date filter

        Returns:
            Audit log entries for the object type.
        """
        query = """SELECT * FROM audit_log
                   WHERE object_type = $1
                   ORDER BY time_stamp DESC
                   LIMIT $2"""
        params = [object_type, limit]

        if start_date:
            query = """SELECT * FROM audit_log
                       WHERE object_type = $1
                       AND time_stamp >= $2
                       ORDER BY time_stamp DESC
                       LIMIT $3"""
            params = [object_type, start_date, limit]

        return await db.fetch(query, *params)

    @mcp.tool()
    async def get_audit_codes() -> dict:
        """Get audit code mappings.

        Returns:
            Dictionary with action, object_type, and source code mappings.
        """
        return {
            "actions": AUDIT_ACTION_MAP,
            "object_types": AUDIT_OBJECT_TYPE_MAP,
            "sources": AUDIT_SOURCE_MAP,
        }

    @mcp.tool()
    async def get_extension_changes(extension_number: str, limit: int = 50) -> list[dict]:
        """Get configuration changes for a specific extension.

        Args:
            extension_number: Extension number
            limit: Maximum records to return

        Returns:
            Audit log entries for the extension.
        """
        return await db.fetch(
            """SELECT
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
               LIMIT $3""",
            f"%{extension_number}%", f"%{extension_number}%", limit
        )

    @mcp.tool()
    async def get_changes_summary(start_date: str, end_date: str) -> list[dict]:
        """Get summary of changes by date and action.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            Summary of changes grouped by date and action.
        """
        return await db.fetch(
            """SELECT
                   DATE(time_stamp) as change_date,
                   action,
                   COUNT(*) as change_count
               FROM audit_log
               WHERE time_stamp >= $1 AND time_stamp <= $2
               GROUP BY DATE(time_stamp), action
               ORDER BY change_date DESC, action""",
            start_date, end_date
        )