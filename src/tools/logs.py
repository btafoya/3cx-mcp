"""
Log parsing MCP tools.

Provides log file access and parsing capabilities.
"""
from mcp.server.fastmcp import FastMCP
from ..logs.parser import LogParser, LogLevel
from datetime import datetime


def register(mcp: FastMCP, log_parser: LogParser):
    """Register log tools."""

    @mcp.tool()
    async def tail_logs(
        follow: bool = False,
        lines: int = 10,
        log_path: str | None = None,
    ) -> list[dict]:
        """Get recent log entries.

        Args:
            follow: If True, note that real-time streaming is not yet implemented
            lines: Number of recent lines to show
            log_path: Optional custom log path

        Returns:
            List of log entries.
        """
        parser = LogParser(log_path) if log_path else log_parser

        # Return static entries
        entries = []
        for entry in parser.get_recent_entries(lines):
            entries.append({
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.value,
                "thread": entry.thread,
                "message": entry.message,
            })

        return entries

    @mcp.tool()
    async def query_logs(
        start_date: str,
        end_date: str,
        level: str | None = None,
        filter_text: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query log entries by date range and filters.

        Args:
            start_date: Start datetime (ISO format)
            end_date: End datetime (ISO format)
            level: Filter by log level (DEBUG, INFO, WARN, ERROR)
            filter_text: Text to search for in messages
            limit: Maximum results to return

        Returns:
            Matching log entries.
        """
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        entries = []
        for entry in log_parser.iter_entries():
            if entry.timestamp < start or entry.timestamp > end:
                continue
            if level and entry.level.value != level.upper():
                continue
            if filter_text and filter_text not in entry.message:
                continue
            entries.append({
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.value,
                "thread": entry.thread,
                "message": entry.message,
            })
            if len(entries) >= limit:
                break

        return entries

    @mcp.tool()
    async def get_call_logs(call_id: str, limit: int = 100) -> list[dict]:
        """Get all log entries for a specific call.

        Args:
            call_id: The unique call identifier (from SIP Call-ID or database ID)
            limit: Maximum results to return

        Returns:
            Log entries associated with the call.
        """
        call_entries = log_parser.find_by_call_id(call_id)
        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.value,
                "message": entry.message,
                "sip_method": entry.sip_message.method.value if entry.sip_message else None,
                "from_number": entry.sip_message.from_number if entry.sip_message else None,
                "to_number": entry.sip_message.to_number if entry.sip_message else None,
            }
            for entry in call_entries[:limit]
        ]

    @mcp.tool()
    async def get_extension_logs(
        extension: str,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get log entries for a specific extension.

        Args:
            extension: Extension number
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Maximum results to return

        Returns:
            Log entries for the extension.
        """
        entries = log_parser.find_by_extension(extension)

        if start_date or end_date:
            start = datetime.fromisoformat(start_date) if start_date else None
            end = datetime.fromisoformat(end_date) if end_date else None

            entries = [
                e for e in entries
                if (not start or e.timestamp >= start)
                and (not end or e.timestamp <= end)
            ]

        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "level": e.level.value,
                "message": e.message,
            }
            for e in entries[:limit]
        ]

    @mcp.tool()
    async def get_errors(
        start_date: str,
        end_date: str,
        severity: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get error and warning log entries.

        Args:
            start_date: Start datetime (ISO format)
            end_date: End datetime (ISO format)
            severity: Filter by severity (ERROR, WARN, FATAL)
            limit: Maximum results to return

        Returns:
            Error log entries.
        """
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        errors = log_parser.get_errors(start, end)

        if severity:
            errors = [e for e in errors if e.level.value == severity.upper()]

        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "level": e.level.value,
                "thread": e.thread,
                "message": e.message,
            }
            for e in errors[:limit]
        ]

    @mcp.tool()
    async def get_routing_decisions(call_id: str) -> list[dict]:
        """Get routing decisions for a call.

        Args:
            call_id: The unique call identifier

        Returns:
            List of routing decisions with timestamps.
        """
        call_entries = log_parser.find_by_call_id(call_id)
        routing = [
            entry.routing_decision
            for entry in call_entries
            if entry.routing_decision
        ]

        return [
            {
                "timestamp": r.timestamp.isoformat(),
                "decision": r.decision,
                "source": r.source,
                "destination": r.destination,
            }
            for r in routing
        ]

    @mcp.tool()
    async def parse_sip_messages(count: int = 50) -> list[dict]:
        """Parse SIP messages from recent log entries.

        Args:
            count: Number of entries to parse

        Returns:
            Parsed SIP messages with method, call-id, from/to numbers.
        """
        results = []
        parsed = 0

        for entry in log_parser.iter_entries():
            sip = log_parser.parse_sip_message(entry)
            if sip:
                results.append({
                    "timestamp": entry.timestamp.isoformat(),
                    "method": sip.method.value,
                    "call_id": sip.call_id,
                    "from_number": sip.from_number,
                    "to_number": sip.to_number,
                    "status": sip.status,
                })
                parsed += 1
                if parsed >= count:
                    break

        return results

    @mcp.tool()
    async def get_log_levels() -> list[dict]:
        """Get available log levels.

        Returns:
            List of log levels.
        """
        return [
            {"level": level.value, "name": level.name}
            for level in LogLevel
        ]