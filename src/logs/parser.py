"""
3CX log file parser.

Parses 3CX system logs to extract call flow information, SIP messages,
and routing decisions.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Iterator
import gzip


class LogLevel(str, Enum):
    """Log level."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class SipMethod(str, Enum):
    """SIP method."""
    INVITE = "INVITE"
    ACK = "ACK"
    BYE = "BYE"
    CANCEL = "CANCEL"
    REGISTER = "REGISTER"
    OPTIONS = "OPTIONS"


@dataclass
class LogEntry:
    """Parsed log entry."""
    timestamp: datetime
    level: LogLevel
    thread: str
    message: str
    raw: str


@dataclass
class SipMessage:
    """Parsed SIP message from log."""
    timestamp: datetime
    method: SipMethod
    call_id: str
    from_number: Optional[str]
    to_number: Optional[str]
    status: Optional[int] = None
    raw: str = ""


@dataclass
class RoutingDecision:
    """Call routing decision parsed from logs."""
    timestamp: datetime
    call_id: str
    decision: str
    source: str
    destination: str


@dataclass
class CallLogEntry:
    """Log entry associated with a call."""
    timestamp: datetime
    level: LogLevel
    message: str
    call_id: Optional[str] = None
    sip_message: Optional[SipMessage] = None
    routing_decision: Optional[RoutingDecision] = None


# Log entry pattern (to be adjusted based on actual log format)
LOG_PATTERN = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) '
    r'\[(?P<thread>\d+)\] '
    r'(?P<level>DEBUG|INFO|WARN|ERROR|FATAL) '
    r'(?P<message>.*)$'
)

# SIP Call-ID pattern
CALL_ID_PATTERN = re.compile(r'Call-ID:\s*<?([^>;\s]+)')

# SIP From/To patterns
FROM_PATTERN = re.compile(r'From:\s*"?sip:([^@"\s]+)@"?')
TO_PATTERN = re.compile(r'To:\s*"?sip:([^@"\s]+)@"?')

# SIP response pattern
SIP_RESPONSE_PATTERN = re.compile(r'SIP/2\.0\s+(\d{3})')

# Routing decision patterns (to be adjusted based on actual log format)
ROUTING_PATTERNS = [
    re.compile(r'Routing call from (\S+) to (\S+)'),
    re.compile(r'Forwarding to (\S+)'),
    re.compile(r'Queue (\S+) -> (\S+)'),
]


class LogParser:
    """Parse 3CX log files."""

    def __init__(self, log_path: str, encoding: str = "utf-8"):
        self.log_path = Path(log_path)
        self.encoding = encoding

    def parse_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line."""
        line = line.strip()
        if not line:
            return None

        # Try primary pattern first
        match = LOG_PATTERN.match(line)
        if not match:
            # Try alternative formats (to be adjusted based on actual logs)
            alt_match = re.match(
                r'^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+'
                r'(?P<level>\w+)\s+'
                r'(?P<message>.*)$',
                line
            )
            if alt_match:
                try:
                    timestamp = datetime.strptime(
                        alt_match.group("timestamp"),
                        "%Y-%m-%d %H:%M:%S"
                    )
                    return LogEntry(
                        timestamp=timestamp,
                        level=LogLevel(alt_match.group("level").upper()),
                        thread="unknown",
                        message=alt_match.group("message").strip(),
                        raw=line
                    )
                except ValueError:
                    return None
            return None

        try:
            timestamp = datetime.strptime(
                match.group("timestamp"),
                "%Y-%m-%d %H:%M:%S.%f"
            )
            return LogEntry(
                timestamp=timestamp,
                level=LogLevel(match.group("level")),
                thread=match.group("thread"),
                message=match.group("message").strip(),
                raw=line
            )
        except ValueError:
            return None

    def parse_sip_message(self, entry: LogEntry) -> Optional[SipMessage]:
        """Extract SIP message from log entry."""
        message = entry.message

        # Check if entry contains SIP method
        for method in SipMethod:
            if method.value in message:
                call_id_match = CALL_ID_PATTERN.search(message)
                from_match = FROM_PATTERN.search(message)
                to_match = TO_PATTERN.search(message)
                response_match = SIP_RESPONSE_PATTERN.search(message)

                return SipMessage(
                    timestamp=entry.timestamp,
                    method=method,
                    call_id=call_id_match.group(1) if call_id_match else "",
                    from_number=from_match.group(1) if from_match else None,
                    to_number=to_match.group(1) if to_match else None,
                    status=int(response_match.group(1)) if response_match else None,
                    raw=message
                )
        return None

    def extract_routing_decision(self, entry: LogEntry) -> Optional[RoutingDecision]:
        """Extract routing decision from log entry."""
        for pattern in ROUTING_PATTERNS:
            match = pattern.search(entry.message)
            if match:
                call_id_match = CALL_ID_PATTERN.search(entry.message)
                return RoutingDecision(
                    timestamp=entry.timestamp,
                    call_id=call_id_match.group(1) if call_id_match else "",
                    decision=match.group(0),
                    source=match.group(1) if match.lastindex >= 1 else "",
                    destination=match.group(2) if match.lastindex >= 2 else ""
                )
        return None

    def iter_entries(self) -> Iterator[LogEntry]:
        """Iterate over all log entries."""
        if not self.log_path.exists():
            return

        open_fn = gzip.open if self.log_path.suffix == ".gz" else open

        try:
            with open_fn(self.log_path, "rt", encoding=self.encoding, errors="replace") as f:
                for line in f:
                    entry = self.parse_line(line)
                    if entry:
                        yield entry
        except (FileNotFoundError, PermissionError):
            pass

    def find_by_call_id(self, call_id: str) -> List[CallLogEntry]:
        """Find all log entries for a specific call."""
        results = []
        for entry in self.iter_entries():
            if call_id in entry.raw:
                call_entry = CallLogEntry(
                    timestamp=entry.timestamp,
                    level=entry.level,
                    message=entry.message,
                    call_id=call_id,
                    sip_message=self.parse_sip_message(entry),
                    routing_decision=self.extract_routing_decision(entry)
                )
                results.append(call_entry)
        return results

    def find_by_extension(self, extension: str) -> List[CallLogEntry]:
        """Find all log entries for a specific extension."""
        results = []
        for entry in self.iter_entries():
            if f"sip:{extension}@" in entry.raw or extension in entry.message:
                call_entry = CallLogEntry(
                    timestamp=entry.timestamp,
                    level=entry.level,
                    message=entry.message
                )
                results.append(call_entry)
        return results

    def get_errors(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[LogEntry]:
        """Get error and warning log entries."""
        errors = []
        for entry in self.iter_entries():
            if entry.level not in (LogLevel.ERROR, LogLevel.FATAL, LogLevel.WARN):
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            errors.append(entry)
        return errors

    def get_recent_entries(self, lines: int = 10) -> List[LogEntry]:
        """Get most recent log entries."""
        entries = list(self.iter_entries())
        return entries[-lines:] if entries else []