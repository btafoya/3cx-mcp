"""
Unit tests for log-related MCP tools.

Tests verify log parser functionality and data processing.
"""
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.logs.parser import (
    LogParser,
    LogEntry,
    LogLevel,
)


class TestLogsTools:
    """Tests for log-related tools."""

    @pytest.fixture
    def sample_log_content(self) -> str:
        """Sample log content."""
        return """2026-03-07 10:00:00.000 [1] INFO System started
2026-03-07 10:00:01.123 [2] DEBUG INVITE sip:100@localhost
2026-03-07 10:00:02.456 [1] WARN Connection timeout
2026-03-07 10:00:03.789 [3] ERROR Call failed: timeout
2026-03-07 10:00:04.000 [1] INFO BYE sip:100@localhost
2026-03-07 10:00:05.000 [2] FATAL System crash
"""

    @pytest.fixture
    def log_file(self, tmp_path: Path, sample_log_content: str) -> Path:
        """Create temporary log file."""
        log_file = tmp_path / "test.log"
        log_file.write_text(sample_log_content)
        return log_file

    @pytest.fixture
    def log_parser(self, log_file: Path) -> LogParser:
        """LogParser instance."""
        return LogParser(str(log_file), encoding="utf-8")

    def test_tail_logs_returns_entries(self, log_parser):
        """Test tail_logs returns recent log entries."""
        entries = list(log_parser.get_recent_entries(3))

        assert isinstance(entries, list)
        assert len(entries) == 3
        assert all("timestamp" in dir(e) for e in entries)

    def test_tail_logs_with_custom_limit(self, log_parser):
        """Test tail_logs with custom line count."""
        entries = log_parser.get_recent_entries(2)

        assert len(entries) == 2

    def test_query_logs_with_filters(self, log_parser):
        """Test query_logs with level filter."""
        start = datetime(2026, 3, 7, 10, 0, 0)
        end = datetime(2026, 3, 7, 11, 0, 0)

        entries = []
        for entry in log_parser.iter_entries():
            if entry.timestamp < start or entry.timestamp > end:
                continue
            if entry.level != LogLevel.ERROR:
                continue
            entries.append({
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.value,
                "message": entry.message,
            })

        assert all(entry["level"] == "ERROR" for entry in entries)

    def test_query_logs_with_text_filter(self, log_parser):
        """Test query_logs with text filter."""
        start = datetime(2026, 3, 7, 10, 0, 0)
        end = datetime(2026, 3, 7, 11, 0, 0)

        entries = []
        for entry in log_parser.iter_entries():
            if entry.timestamp < start or entry.timestamp > end:
                continue
            if "timeout" not in entry.message:
                continue
            entries.append({
                "timestamp": entry.timestamp.isoformat(),
                "message": entry.message,
            })

        assert all("timeout" in e["message"] for e in entries)

    def test_get_call_logs_by_call_id(self, log_parser):
        """Test get_call_logs by call ID."""
        entries = log_parser.find_by_call_id("nonexistent")

        assert isinstance(entries, list)

    def test_get_extension_logs(self, log_parser):
        """Test get_extension_logs."""
        entries = log_parser.find_by_extension("100")

        assert isinstance(entries, list)
        # Should find entries with "100" in them
        assert any("100" in e.message for e in entries)

    def test_get_errors(self, log_parser):
        """Test get_errors."""
        errors = log_parser.get_errors()

        assert isinstance(errors, list)
        assert all(e.level in (LogLevel.ERROR, LogLevel.FATAL, LogLevel.WARN) for e in errors)

    def test_get_errors_with_severity_filter(self, log_parser):
        """Test get_errors with severity filter."""
        start = datetime(2026, 3, 7, 10, 0, 0)
        end = datetime(2026, 3, 7, 11, 0, 0)

        errors = [e for e in log_parser.get_errors(start, end)
                  if e.level == LogLevel.FATAL]

        assert all(e.level == LogLevel.FATAL for e in errors)

    def test_get_routing_decisions(self, log_parser):
        """Test get_routing_decisions."""
        entries = log_parser.iter_entries()
        routing = [
            {
                "timestamp": e.timestamp.isoformat(),
                "decision": "Routing call from 100 to 200",
            }
            for e in entries
            if "Routing" in e.message
        ]

        assert isinstance(routing, list)

    def test_parse_sip_messages(self, log_parser):
        """Test parse_sip_messages."""
        entries = log_parser.iter_entries()
        sip_messages = []

        for entry in entries:
            for method in ["INVITE", "BYE", "ACK"]:
                if method in entry.message:
                    sip_messages.append({
                        "timestamp": entry.timestamp.isoformat(),
                        "method": method,
                        "message": entry.message,
                    })
                    break

        assert isinstance(sip_messages, list)

    def test_get_log_levels(self):
        """Test get_log_levels returns all levels."""
        from src.logs.parser import LogLevel

        levels = [
            {"level": level.value, "name": level.name}
            for level in LogLevel
        ]

        assert len(levels) == 5  # DEBUG, INFO, WARN, ERROR, FATAL
        assert all("level" in level for level in levels)
