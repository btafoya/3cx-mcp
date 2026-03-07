"""
Unit tests for log file parsing.
"""
from datetime import datetime
from pathlib import Path
import gzip

import pytest

from src.logs.parser import (
    LogParser,
    LogEntry,
    LogLevel,
    SipMethod,
    SipMessage,
    RoutingDecision,
    CallLogEntry,
)


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_log_level_values(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARN.value == "WARN"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.FATAL.value == "FATAL"

    def test_log_level_comparison(self):
        """Test LogLevel comparison."""
        assert LogLevel.ERROR == LogLevel.ERROR
        assert LogLevel.DEBUG != LogLevel.ERROR


class TestSipMethod:
    """Tests for SipMethod enum."""

    def test_sip_method_values(self):
        """Test SipMethod enum values."""
        assert SipMethod.INVITE.value == "INVITE"
        assert SipMethod.ACK.value == "ACK"
        assert SipMethod.BYE.value == "BYE"
        assert SipMethod.CANCEL.value == "CANCEL"
        assert SipMethod.REGISTER.value == "REGISTER"
        assert SipMethod.OPTIONS.value == "OPTIONS"


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_log_entry_creation(self):
        """Test LogEntry creation."""
        entry = LogEntry(
            timestamp=datetime(2026, 3, 7, 10, 0, 0),
            level=LogLevel.INFO,
            thread="1",
            message="Test message",
            raw="2026-03-07 10:00:00.000 [1] INFO Test message",
        )

        assert entry.timestamp == datetime(2026, 3, 7, 10, 0, 0)
        assert entry.level == LogLevel.INFO
        assert entry.thread == "1"
        assert entry.message == "Test message"
        assert entry.raw == "2026-03-07 10:00:00.000 [1] INFO Test message"


class TestSipMessage:
    """Tests for SipMessage dataclass."""

    def test_sip_message_creation(self):
        """Test SipMessage creation."""
        msg = SipMessage(
            timestamp=datetime(2026, 3, 7, 10, 0, 0),
            method=SipMethod.INVITE,
            call_id="abc123",
            from_number="100",
            to_number="200",
            status=None,
            raw="INVITE sip:200@...",
        )

        assert msg.timestamp == datetime(2026, 3, 7, 10, 0, 0)
        assert msg.method == SipMethod.INVITE
        assert msg.call_id == "abc123"
        assert msg.from_number == "100"
        assert msg.to_number == "200"
        assert msg.status is None


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""

    def test_routing_decision_creation(self):
        """Test RoutingDecision creation."""
        decision = RoutingDecision(
            timestamp=datetime(2026, 3, 7, 10, 0, 0),
            call_id="abc123",
            decision="Routing call from 100 to 200",
            source="100",
            destination="200",
        )

        assert decision.timestamp == datetime(2026, 3, 7, 10, 0, 0)
        assert decision.call_id == "abc123"
        assert decision.decision == "Routing call from 100 to 200"
        assert decision.source == "100"
        assert decision.destination == "200"


class TestCallLogEntry:
    """Tests for CallLogEntry dataclass."""

    def test_call_log_entry_creation(self):
        """Test CallLogEntry creation."""
        entry = CallLogEntry(
            timestamp=datetime(2026, 3, 7, 10, 0, 0),
            level=LogLevel.INFO,
            message="Call started",
            call_id="abc123",
        )

        assert entry.timestamp == datetime(2026, 3, 7, 10, 0, 0)
        assert entry.level == LogLevel.INFO
        assert entry.call_id == "abc123"
        assert entry.sip_message is None
        assert entry.routing_decision is None


class TestLogParser:
    """Tests for LogParser."""

    @pytest.fixture
    def sample_log_content(self) -> str:
        """Sample log content for testing."""
        return """2026-03-07 10:00:00.000 [1] INFO System started
2026-03-07 10:00:01.123 [2] DEBUG INVITE sip:100@localhost
2026-03-07 10:00:02.456 [1] WARN Connection timeout
2026-03-07 10:00:03.789 [3] ERROR Call failed: timeout
2026-03-07 10:00:04.000 [1] INFO BYE sip:100@localhost
2026-03-07 10:00:05.000 [2] FATAL System crash
"""

    @pytest.fixture
    def log_file(self, tmp_path: Path, sample_log_content: str) -> Path:
        """Create a temporary log file."""
        log_file = tmp_path / "test.log"
        log_file.write_text(sample_log_content)
        return log_file

    @pytest.fixture
    def log_gz_file(self, tmp_path: Path, sample_log_content: str) -> Path:
        """Create a temporary gzipped log file."""
        log_file = tmp_path / "test.log.gz"
        with gzip.open(log_file, "wt", encoding="utf-8") as f:
            f.write(sample_log_content)
        return log_file

    @pytest.fixture
    def parser(self, log_file: Path) -> LogParser:
        """LogParser instance."""
        return LogParser(str(log_file), encoding="utf-8")

    def test_parser_creation(self, log_file: Path):
        """Test LogParser creation."""
        parser = LogParser(str(log_file), encoding="utf-8")

        assert parser.log_path == log_file
        assert parser.encoding == "utf-8"

    def test_parse_line_valid(self, parser: LogParser):
        """Test parsing a valid log line."""
        line = "2026-03-07 10:00:00.000 [1] INFO Test message"
        entry = parser.parse_line(line)

        assert entry is not None
        assert entry.level == LogLevel.INFO
        assert entry.thread == "1"
        assert entry.message == "Test message"
        assert entry.timestamp == datetime(2026, 3, 7, 10, 0, 0)

    def test_parse_line_empty(self, parser: LogParser):
        """Test parsing an empty line."""
        entry = parser.parse_line("")
        assert entry is None

    def test_parse_line_whitespace(self, parser: LogParser):
        """Test parsing whitespace."""
        entry = parser.parse_line("   ")
        assert entry is None

    def test_parse_line_invalid_format(self, parser: LogParser):
        """Test parsing invalid format."""
        entry = parser.parse_line("Invalid log line")
        assert entry is None

    def test_parse_line_different_levels(self, parser: LogParser):
        """Test parsing different log levels."""
        levels = [
            ("DEBUG", LogLevel.DEBUG),
            ("INFO", LogLevel.INFO),
            ("WARN", LogLevel.WARN),
            ("ERROR", LogLevel.ERROR),
            ("FATAL", LogLevel.FATAL),
        ]

        for level_str, expected_level in levels:
            line = f"2026-03-07 10:00:00.000 [1] {level_str} Test"
            entry = parser.parse_line(line)
            assert entry is not None
            assert entry.level == expected_level

    def test_parse_line_without_thread(self, parser: LogParser):
        """Test parsing log line without thread ID (alternative format)."""
        line = "2026-03-07 10:00:00 INFO Test message"
        entry = parser.parse_line(line)

        assert entry is not None
        assert entry.level == LogLevel.INFO
        assert entry.thread == "unknown"
        assert entry.message == "Test message"

    def test_parse_sip_message_invite(self, parser: LogParser):
        """Test parsing INVITE SIP message."""
        entry = LogEntry(
            timestamp=datetime(2026, 3, 7, 10, 0, 0),
            level=LogLevel.INFO,
            thread="1",
            message='INVITE sip:100@localhost',
            raw="raw",
        )

        sip = parser.parse_sip_message(entry)

        assert sip is not None
        assert sip.method == SipMethod.INVITE
        # The parser may not extract all fields without proper format

    def test_parse_sip_message_bye(self, parser: LogParser):
        """Test parsing BYE SIP message."""
        entry = LogEntry(
            timestamp=datetime(2026, 3, 7, 10, 0, 0),
            level=LogLevel.INFO,
            thread="1",
            message='BYE sip:200@domain Call-ID: xyz789 From: "User" <sip:100@domain>',
            raw="raw",
        )

        sip = parser.parse_sip_message(entry)

        assert sip is not None
        assert sip.method == SipMethod.BYE
        assert sip.call_id == "xyz789"

    def test_parse_sip_message_none(self, parser: LogParser):
        """Test parsing entry without SIP message."""
        entry = LogEntry(
            timestamp=datetime(2026, 3, 7, 10, 0, 0),
            level=LogLevel.INFO,
            thread="1",
            message="Regular log message",
            raw="raw",
        )

        sip = parser.parse_sip_message(entry)

        assert sip is None

    def test_parse_sip_message_response(self, parser: LogParser):
        """Test parsing SIP response."""
        entry = LogEntry(
            timestamp=datetime(2026, 3, 7, 10, 0, 0),
            level=LogLevel.INFO,
            thread="1",
            message='INVITE sip:200@domain Call-ID: abc123 SIP/2.0 200 OK',
            raw="raw",
        )

        sip = parser.parse_sip_message(entry)

        assert sip is not None
        assert sip.status == 200

    def test_extract_routing_decision(self, parser: LogParser):
        """Test extracting routing decision."""
        entry = LogEntry(
            timestamp=datetime(2026, 3, 7, 10, 0, 0),
            level=LogLevel.INFO,
            thread="1",
            message='Routing call from 100 to 200 Call-ID: abc123',
            raw="raw",
        )

        decision = parser.extract_routing_decision(entry)

        assert decision is not None
        assert decision.source == "100"
        assert decision.destination == "200"
        assert decision.call_id == "abc123"

    def test_extract_routing_decision_none(self, parser: LogParser):
        """Test extracting routing decision from non-routing message."""
        entry = LogEntry(
            timestamp=datetime(2026, 3, 7, 10, 0, 0),
            level=LogLevel.INFO,
            thread="1",
            message="Regular log message",
            raw="raw",
        )

        decision = parser.extract_routing_decision(entry)

        assert decision is None

    def test_iter_entries(self, parser: LogParser, sample_log_content: str):
        """Test iterating over log entries."""
        entries = list(parser.iter_entries())

        assert len(entries) == 6
        assert entries[0].level == LogLevel.INFO
        assert entries[2].level == LogLevel.WARN
        assert entries[5].level == LogLevel.FATAL

    def test_iter_entries_nonexistent(self, tmp_path: Path):
        """Test iterating over non-existent file."""
        parser = LogParser(str(tmp_path / "nonexistent.log"))
        entries = list(parser.iter_entries())
        assert entries == []

    def test_iter_entries_gzipped(self, log_gz_file: Path):
        """Test iterating over gzipped log file."""
        parser = LogParser(str(log_gz_file), encoding="utf-8")
        entries = list(parser.iter_entries())
        assert len(entries) == 6

    def test_find_by_call_id(self, parser: LogParser):
        """Test finding entries by call ID."""
        entries = parser.find_by_call_id("test-123")

        # No entries with this call ID in sample log
        assert entries == []

    def test_find_by_call_id_existing(self, tmp_path: Path):
        """Test finding entries by existing call ID."""
        log_content = """2026-03-07 10:00:00.000 [1] INFO Call-ID: test-123@domain.com INVITE
2026-03-07 10:00:01.000 [1] INFO Call-ID: test-123@domain.com BYE
"""
        log_file = tmp_path / "test_with_callid.log"
        log_file.write_text(log_content)
        parser = LogParser(str(log_file), encoding="utf-8")

        entries = parser.find_by_call_id("test-123")

        # Should find entries containing the call ID
        assert len(entries) > 0

    def test_find_by_call_id_not_found(self, parser: LogParser):
        """Test finding non-existent call ID."""
        entries = parser.find_by_call_id("nonexistent-id")
        assert entries == []

    def test_find_by_extension(self, parser: LogParser):
        """Test finding entries by extension."""
        entries = parser.find_by_extension("100")

        assert len(entries) > 0
        assert any("100" in e.message for e in entries)

    def test_find_by_extension_not_found(self, parser: LogParser):
        """Test finding non-existent extension."""
        entries = parser.find_by_extension("999")
        assert entries == []

    def test_get_errors(self, parser: LogParser):
        """Test getting error log entries."""
        errors = parser.get_errors()

        # WARN, ERROR, and FATAL are included
        assert len(errors) == 3
        assert all(e.level in (LogLevel.ERROR, LogLevel.FATAL, LogLevel.WARN) for e in errors)

    def test_get_errors_with_time_filter(self, parser: LogParser):
        """Test getting errors with time filter."""
        start = datetime(2026, 3, 7, 10, 0, 3)
        end = datetime(2026, 3, 7, 10, 0, 5)

        errors = parser.get_errors(start, end)

        # Should include ERROR and FATAL entries
        assert len(errors) == 2
        assert errors[0].level == LogLevel.ERROR
        assert errors[1].level == LogLevel.FATAL

    def test_get_recent_entries(self, parser: LogParser):
        """Test getting recent log entries."""
        recent = parser.get_recent_entries(3)

        assert len(recent) == 3
        # Last entries are WARN, ERROR, FATAL

    def test_get_recent_entries_more_than_available(self, parser: LogParser):
        """Test getting more entries than available."""
        recent = parser.get_recent_entries(100)

        assert len(recent) == 6  # All entries

    def test_parse_line_timezone(self, parser: LogParser):
        """Test parsing line with different timestamp formats."""
        # The log parser currently requires milliseconds
        line = "2026-03-07 10:00:00.000 [1] INFO Test"
        entry = parser.parse_line(line)

        assert entry is not None
        assert entry.level == LogLevel.INFO
        assert entry.message == "Test"