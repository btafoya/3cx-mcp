# 3CX Call Flow Debugging Add-On - Design Document

## 1. Overview

The 3CX Call Flow Debugging Add-On is an MCP server that runs directly on the 3CX server to provide call flow debugging capabilities without requiring enterprise XAPI licensing. It uses a hybrid approach: direct PostgreSQL database access for structured CRUD operations combined with log file parsing for detailed flow tracing.

**Target Edition:** 3CX Professional (Linux)

**Key Difference from XAPI Client:** This add-on connects directly to the 3CX PostgreSQL database and parses server log files instead of using the enterprise-only XAPI REST API.

### Quick Reference: Core Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `cl_calls` | Call summary | `id`, `start_time`, `end_time`, `is_answered` |
| `cl_participants` | Participants | `id`, `dn_type`, `dn`, `caller_number`, `display_name` |
| `cl_segments` | Call flow | `call_id`, `seq_order`, `src_part_id`, `dst_part_id` |
| `cl_party_info` | Party details | `call_id`, `role`, `is_inbound`, `billing_cost` |
| `cdroutput` | Full CDR | `cdr_id`, `source_*`, `destination_*`, `termination_reason` |
| `recordings` | Call recordings | `id_recording`, `recording_url`, `sentiment_score` |
| `s_voicemail` | Voicemail | `idcallcent_queuecalls`, `caller`, `callee`, `heard` |
| `callcent_queuecalls` | Queue stats | `q_num`, `ts_waiting`, `call_result` |
| `audit_log` | Audit trail | `time_stamp`, `user_name`, `action`, `prev_data`, `new_data` |

### DN Type Codes

| Code | Type |
|------|------|
| 0 | Extension |
| 1 | External Line/Provider |
| 2 | Ring Group/Queue |
| 5 | Voicemail |
| 13 | Inbound Routing |

---

## 2. System Architecture

### 2.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Claude Code (LLM)                               │
│                                                                              │
│  "Show me the complete flow of failed call 12345"                             │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ MCP Protocol (stdio)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    3CX Debugging MCP Server (FastMCP)                        │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         Tool Registry                                   │ │
│  │  • trace_call()              • get_active_calls()                       │ │
│  │  • debug_failed_call()       • list_extensions()                        │ │
│  │  • tail_logs()              • list_queues()                            │ │
│  │  • query_logs()             • create_extension()                       │ │
│  │  • get_call_statistics()    • update_routing()                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                     │
│         ┌──────────────────────────────┼──────────────────────────────┐     │
│         │                              │                              │     │
│         ▼                              ▼                              │     │
│  ┌──────────────────┐         ┌──────────────────┐                     │     │
│  │  Database Layer  │         │   Log Parser     │                     │     │
│  │                  │         │                  │                     │     │
│  │ • Query Builder  │         │ • Log Tailer     │                     │     │
│  │ • Connection Mgr │         │ • SIP Parser     │                     │     │
│  │ • Transaction Mgr│         │ • Error Extractor│                     │     │
│  └────────┬─────────┘         └────────┬─────────┘                     │     │
│           │                            │                               │     │
│           ▼                            ▼                               │     │
│  ┌──────────────────┐         ┌──────────────────┐                     │     │
│  │  PostgreSQL      │         │  3CX Log Files   │                     │     │
│  │  Connection Pool│         │  (File System)   │                     │     │
│  └──────────────────┘         └──────────────────┘                     │     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────┐
                        │      3CX PostgreSQL       │
                        │                          │
                        │  • Calls                 │
                        │  • Extensions            │
                        │  • Queues                │
                        │  • Trunks                │
                        │  • CDR                   │
                        │  • ActiveCalls           │
                        └──────────────────────────┘
```

### 2.2 Data Flow

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ Query Call Trace (Hybrid)                                                          │
├────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│  LLM → MCP Tool (trace_call)                                                      │
│       │                                                                            │
│       ├─→ Database Layer: Query Call record by ID                                  │
│       │       │                                                                    │
│       │       └─→ Returns: caller, callee, start_time, status, trunk, queue       │
│       │                                                                            │
│       ├─→ Log Parser: Search logs for Call ID                                      │
│       │       │                                                                    │
│       │       ├─→ Parse SIP messages (INVITE, ACK, BYE)                           │
│       │       ├─→ Extract routing decisions                                       │
│       │       └─→ Identify errors/warnings                                         │
│       │                                                                            │
│       └─→ Combine results → Return to LLM                                          │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────┐
│ Tail Real-time Logs                                                               │
├────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│  LLM → MCP Tool (tail_logs, follow=True)                                          │
│       │                                                                            │
│       ├─→ Log Parser: Open log file, seek to end                                 │
│       │       │                                                                    │
│       │       └─→ Watch for new lines (inotify or poll)                           │
│       │               │                                                            │
│       │               └─→ Parse each new line, emit to LLM                        │
│       │                                                                            │
└────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────┐
│ Create Extension (Write)                                                           │
├────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│  LLM → MCP Tool (create_extension)                                                 │
│       │                                                                            │
│       ├─→ Database Layer: Begin transaction                                       │
│       │       │                                                                    │
│       │       ├─→ Insert into Extensions table                                     │
│       │       ├─→ Insert into Users table (if applicable)                         │
│       │       └─→ Commit transaction                                              │
│       │                                                                            │
│       ├─→ Log operation to audit log                                              │
│       │                                                                            │
│       └─→ Return success to LLM                                                   │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Specification

### 3.1 Directory Structure

```
3cx-mcp-debugging/
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastMCP server entry point
│   ├── config.py                  # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py          # PostgreSQL connection pool
│   │   ├── schema.py              # Database schema models
│   │   ├── queries/
│   │   │   ├── __init__.py
│   │   │   ├── calls.py           # Call record queries
│   │   │   ├── extensions.py      # Extension queries
│   │   │   ├── queues.py          # Queue queries
│   │   │   ├── trunks.py          # Trunk queries
│   │   │   └── statistics.py      # Aggregate queries
│   │   └── writes/
│   │       ├── __init__.py
│   │       ├── extensions.py      # Extension write operations
│   │       ├── queues.py          # Queue write operations
│   │       └── routing.py         # Routing rule operations
│   ├── logs/
│   │   ├── __init__.py
│   │   ├── parser.py              # Log file parser
│   │   ├── sip.py                 # SIP message parser
│   │   ├── tailer.py              # Real-time log tailing
│   │   └── paths.py               # Log file path resolution
│   ├── models/
│   │   ├── __init__.py
│   │   ├── call.py                # Call record models
│   │   ├── extension.py           # Extension models
│   │   ├── queue.py               # Queue models
│   │   ├── trunk.py               # Trunk models
│   │   └── log.py                 # Log entry models
│   └── tools/
│       ├── __init__.py
│       ├── calls.py               # Call-related tools
│       ├── extensions.py          # Extension tools
│       ├── queues.py              # Queue tools
│       ├── trunks.py              # Trunk tools
│       ├── logs.py                # Log parsing tools
│       └── hybrid.py              # Combined database+log tools
├── tests/
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_log_parser.py
│   └── test_tools/
├── pyproject.toml
├── requirements.txt
├── README-debugging.md
├── DESIGN-debugging.md           # This file
└── REQUIREMENTS-debugging.md
```

---

### 3.2 Configuration Module (config.py)

```python
"""
Configuration management for 3CX Debugging MCP Server.

Configuration is loaded from environment variables and 3CX config files.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class DatabaseConfig:
    """PostgreSQL database connection configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "3cxpbx"
    user: str = "3cxpbx"
    password: Optional[str] = None
    socket_dir: str = "/var/run/postgresql"
    use_socket: bool = True
    pool_size: int = 5
    max_overflow: int = 10

@dataclass
class LogConfig:
    """Log file configuration."""
    main_log_path: str = "/var/lib/3cxpbx/Bin/3CXPhoneSystem.log"
    log_dir: str = "/var/lib/3cxpbx/Bin"
    instance_log_dir: str = "/var/lib/3cxpbx/Instance1/Data/Logs"
    encoding: str = "utf-8"
    rotation_pattern: str = "3CXPhoneSystem-*.log"

@dataclass
class ServerConfig:
    """Server configuration."""
    mcp_name: str = "3cx-debugging"
    log_level: str = "INFO"
    enable_write_operations: bool = True  # Can be disabled for safety
    audit_log_path: str = "/var/log/3cx-mcp-debugging/audit.log"

@dataclass
class Config:
    """Complete configuration."""
    database: DatabaseConfig
    logs: LogConfig
    server: ServerConfig

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            database=DatabaseConfig(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", "5432")),
                database=os.getenv("DB_NAME", "3cxpbx"),
                user=os.getenv("DB_USER", "3cxpbx"),
                password=os.getenv("DB_PASSWORD"),
                socket_dir=os.getenv("DB_SOCKET_DIR", "/var/run/postgresql"),
                use_socket=os.getenv("DB_USE_SOCKET", "true").lower() == "true",
            ),
            logs=LogConfig(
                main_log_path=os.getenv("LOG_PATH", "/var/lib/3cxpbx/Bin/3CXPhoneSystem.log"),
                log_dir=os.getenv("LOG_DIR", "/var/lib/3cxpbx/Bin"),
            ),
            server=ServerConfig(
                mcp_name=os.getenv("MCP_NAME", "3cx-debugging"),
                enable_write_operations=os.getenv("ENABLE_WRITES", "true").lower() == "true",
            )
        )

    def validate(self) -> None:
        """Validate configuration."""
        if self.database.use_socket:
            if not Path(self.database.socket_dir).exists():
                raise ValueError(f"PostgreSQL socket directory not found: {self.database.socket_dir}")
        else:
            if not self.database.password:
                raise ValueError("Database password required when not using socket")

        if not Path(self.logs.main_log_path).exists():
            raise ValueError(f"Main log file not found: {self.logs.main_log_path}")

        Path(self.server.audit_log_path).parent.mkdir(parents=True, exist_ok=True)
```

---

### 3.3 Database Connection Module (database/connection.py)

```python
"""
PostgreSQL connection pool and query execution.

Uses asyncpg for high-performance async database access.
"""
import asyncpg
from contextlib import asynccontextmanager
from typing import Any, Optional, List
from .config import DatabaseConfig

class DatabaseError(Exception):
    """Base database error."""
    pass

class ConnectionError(DatabaseError):
    """Failed to connect to database."""
    pass

class QueryError(DatabaseError):
    """Query execution failed."""
    def __init__(self, query: str, cause: Exception):
        self.query = query
        self.cause = cause
        super().__init__(f"Query failed: {cause}")

class DatabasePool:
    """PostgreSQL connection pool."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """Initialize connection pool."""
        if self.config.use_socket:
            # Connect via Unix socket
            dsn = f"user={self.config.user} dbname={self.config.database} host={self.config.socket_dir}"
        else:
            dsn = (
                f"postgresql://{self.config.user}:{self.config.password}"
                f"@{self.config.host}:{self.config.port}/{self.config.database}"
            )

        try:
            self._pool = await asyncpg.create_pool(
                dsn,
                min_size=1,
                max_size=self.config.pool_size,
                command_timeout=30,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to create pool: {e}")

    async def close(self) -> None:
        """Close all connections."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def connection(self):
        """Get a connection from the pool."""
        if not self._pool:
            await self.initialize()
        async with self._pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def transaction(self):
        """Get a connection with an active transaction."""
        async with self.connection() as conn:
            async with conn.transaction():
                yield conn

    async def execute(self, query: str, *args, **kwargs) -> str:
        """Execute a query and return the status."""
        async with self.connection() as conn:
            try:
                return await conn.execute(query, *args, **kwargs)
            except Exception as e:
                raise QueryError(query, e)

    async def fetch(self, query: str, *args, **kwargs) -> List[dict]:
        """Execute a query and return results as list of dicts."""
        async with self.connection() as conn:
            try:
                rows = await conn.fetch(query, *args, **kwargs)
                return [dict(row) for row in rows]
            except Exception as e:
                raise QueryError(query, e)

    async def fetchone(self, query: str, *args, **kwargs) -> Optional[dict]:
        """Execute a query and return first result as dict."""
        results = await self.fetch(query, *args, **kwargs)
        return results[0] if results else None

    async def fetchval(self, query: str, *args, **kwargs) -> Any:
        """Execute a query and return single value."""
        async with self.connection() as conn:
            try:
                return await conn.fetchval(query, *args, **kwargs)
            except Exception as e:
                raise QueryError(query, e)
```

---

### 3.4 Database Schema Models (database/schema.py)

```python
"""
Database table schema definitions.

Note: Actual schema may vary by 3CX version. These are expected table structures
to be verified during initial setup.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class CallStatus(str, Enum):
    """Call status values (from is_answered field)."""
    ANSWERED = "t"
    NOT_ANSWERED = "f"

class CallDirection(str, Enum):
    """Call direction (from cl_party_info.is_inbound)."""
    INBOUND = "t"
    OUTBOUND = "f"

class DnType(str, Enum):
    """DN type codes from cl_participants.dn_type."""
    EXTENSION = "0"
    EXTERNAL_LINE = "1"
    RING_GROUP = "2"
    VOICEMAIL = "5"
    INBOUND_ROUTING = "13"

class SegmentType(str, Enum):
    """Segment type codes from cl_segments.type."""
    RINGING = "1"
    CONNECTED = "2"

@dataclass
class CallRecord:
    """Call record from cl_calls table."""
    id: int
    start_time: datetime
    end_time: Optional[datetime]
    is_answered: bool  # PostgreSQL boolean (t/f)
    ringing_dur: str  # INTERVAL type
    talking_dur: str  # INTERVAL type
    q_wait_dur: str  # INTERVAL type
    call_history_id: Optional[str]  # UUID
    duplicated: bool
    migrated: bool

    @property
    def duration_seconds(self) -> Optional[int]:
        """Get talking duration in seconds."""
        if self.talking_dur:
            h, m, s = self.talking_dur.split(":")
            return int(h) * 3600 + int(m) * 60 + int(float(s))
        return None

@dataclass
class Participant:
    """Participant record from cl_participants table."""
    id: int
    dn_type: int  # 0=extension, 1=external, 2=ring_group, 5=voicemail, 13=inbound
    dn: str
    caller_number: str
    display_name: str
    dn_class: int
    firstlastname: str
    did_number: str
    crm_contact: str

@dataclass
class Segment:
    """Call segment from cl_segments table."""
    id: int
    call_id: int
    seq_order: int
    seq_group: int
    src_part_id: int
    dst_part_id: int
    start_time: datetime
    end_time: datetime
    type: int  # 1=ringing, 2=connected
    action_id: int
    action_party_id: Optional[int]
    call_history_id: Optional[str]

@dataclass
class PartyInfo:
    """Party info from cl_party_info table."""
    id: int
    call_id: int
    info_id: int
    role: int
    is_inbound: bool
    end_status: int
    forward_reason: int
    failure_reason: int
    start_time: datetime
    answer_time: Optional[datetime]
    end_time: datetime
    billing_code: Optional[str]
    billing_ratename: Optional[str]
    billing_rate: Optional[int]
    billing_cost: Optional[Decimal]
    billing_duration: str  # INTERVAL
    recording_url: Optional[str]

@dataclass
class CdrOutput:
    """CDR record from cdroutput table."""
    cdr_id: str  # UUID
    call_history_id: str  # UUID
    source_participant_id: str  # UUID
    source_entity_type: str  # extension, external_line, script, etc.
    source_dn_number: str
    source_dn_type: str
    source_dn_name: str
    source_participant_name: str
    source_participant_phone_number: str
    source_participant_is_incoming: bool
    destination_participant_id: str  # UUID
    destination_entity_type: str
    destination_dn_number: str
    destination_dn_type: str
    destination_dn_name: str
    destination_participant_name: str
    creation_method: str
    termination_reason: str
    cdr_started_at: datetime
    cdr_ended_at: datetime
    cdr_answered_at: Optional[datetime]

@dataclass
class Recording:
    """Recording record from recordings table."""
    id_recording: int
    cl_participants_id: Optional[int]
    recording_url: str
    start_time: datetime
    end_time: datetime
    transcription: Optional[str]
    call_type: int  # 1=inbound, 2=outbound
    sentiment_score: Optional[int]  # 1-5
    summary: Optional[str]
    cdr_id: str  # UUID
    transcribed: bool
    queued_dn: Optional[str]

@dataclass
class Voicemail:
    """Voicemail record from s_voicemail table."""
    idcallcent_queuecalls: int
    wav_file: str
    callee: str
    caller: str
    caller_name: str
    duration: int  # seconds
    created_time: str  # Unix timestamp
    heard: bool
    transcription: Optional[str]
    sentiment_score: Optional[int]

@dataclass
class QueueStats:
    """Queue statistics from callcent_queuecalls table."""
    idcallcent_queuecalls: int
    q_num: str  # Queue number
    time_start: datetime
    time_end: datetime
    ts_waiting: str  # INTERVAL
    ts_polling: str  # INTERVAL
    ts_servicing: str  # INTERVAL
    count_polls: int
    count_dialed: int
    count_rejected: int
    call_result: str  # WP, ANSWERED, ABANDONED, TIMEOUT
    from_displayname: str

@dataclass
class AuditLog:
    """Audit log entry from audit_log table."""
    id: int
    time_stamp: datetime
    source: int
    ip: str
    action: int
    object_type: int
    user_name: str
    object_name: str
    prev_data: dict  # JSONB
    new_data: dict  # JSONB

# Verified database tables from 3CX v20.0.8 Professional
TABLES = {
    "cl_calls": {
        "columns": ["id", "start_time", "end_time", "is_answered",
                   "ringing_dur", "talking_dur", "q_wait_dur",
                   "call_history_id", "duplicated", "migrated"],
        "primary_key": "id",
        "description": "Core call summary records",
    },
    "cl_participants": {
        "columns": ["id", "dn_type", "dn", "caller_number", "display_name",
                   "dn_class", "firstlastname", "did_number", "crm_contact"],
        "primary_key": "id",
        "description": "Call participants (extensions, trunks, queues)",
    },
    "cl_segments": {
        "columns": ["id", "call_id", "seq_order", "seq_group",
                   "src_part_id", "dst_part_id", "start_time", "end_time",
                   "type", "action_id", "action_party_id", "call_history_id"],
        "primary_key": "id",
        "description": "Call flow segments (routing steps)",
    },
    "cl_party_info": {
        "columns": ["id", "call_id", "info_id", "role", "is_inbound",
                   "end_status", "forward_reason", "failure_reason",
                   "start_time", "answer_time", "end_time",
                   "billing_code", "billing_ratename", "billing_rate",
                   "billing_cost", "billing_duration", "recording_url"],
        "primary_key": "id",
        "description": "Detailed party info with billing",
    },
    "cdroutput": {
        "columns": ["cdr_id", "call_history_id",
                   "source_participant_id", "source_entity_type",
                   "source_dn_number", "source_dn_type", "source_dn_name",
                   "destination_participant_id", "destination_entity_type",
                   "destination_dn_number", "destination_dn_type", "destination_dn_name",
                   "creation_method", "termination_reason",
                   "cdr_started_at", "cdr_ended_at", "cdr_answered_at"],
        "primary_key": "cdr_id",
        "description": "Full CDR with complete routing path",
    },
    "recordings": {
        "columns": ["id_recording", "cl_participants_id", "recording_url",
                   "start_time", "end_time", "transcription",
                   "call_type", "sentiment_score", "summary", "cdr_id"],
        "primary_key": "id_recording",
        "description": "Call recording metadata with AI analysis",
    },
    "s_voicemail": {
        "columns": ["idcallcent_queuecalls", "__name", "wav_file",
                   "callee", "caller", "caller_name", "duration",
                   "created_time", "heard", "transcription", "sentiment_score"],
        "primary_key": "idcallcent_queuecalls",
        "description": "Voicemail messages",
    },
    "callcent_queuecalls": {
        "columns": ["idcallcent_queuecalls", "q_num", "time_start", "time_end",
                   "ts_waiting", "ts_polling", "ts_servicing",
                   "call_result", "from_displayname"],
        "primary_key": "idcallcent_queuecalls",
        "description": "Queue call statistics",
    },
    "audit_log": {
        "columns": ["id", "time_stamp", "source", "ip", "action",
                   "object_type", "user_name", "object_name",
                   "prev_data", "new_data"],
        "primary_key": "id",
        "description": "Configuration change audit trail",
    },
    "cl_quality": {
        "columns": ["call_history_id", "call_id", "time_stamp",
                   "a_caller", "b_caller", "a_codec", "b_codec",
                   "a_mos_from_pbx", "b_mos_from_pbx",
                   "a_rtt", "b_rtt", "a_rx_loss", "b_rx_loss"],
        "primary_key": "call_history_id",
        "description": "Call quality metrics (MOS, jitter, packet loss)",
    },
}

# DN Type codes
DN_TYPE = {
    0: "extension",
    1: "external_line",
    2: "ring_group",
    5: "voicemail",
    13: "inbound_routing",
}

# CDR creation methods
CDR_CREATION_METHOD = {
    "call_init": "Initial call creation",
    "divert": "Diverted/forwarded",
    "transfer": "Transferred",
    "route_to": "Routed to destination",
    "polling": "Polling for available agents",
}

# CDR termination reasons
CDR_TERMINATION_REASON = {
    "dst_participant_terminated": "Destination ended call",
    "src_participant_terminated": "Source ended call",
    "continued_in": "Call continued elsewhere",
    "cancelled": "Call was cancelled",
    "redirected": "Call was redirected",
    "polling": "Timed out during polling",
    "no_route": "No route available",
    "completed_elsewhere": "Answered elsewhere",
}

# NOTE: active_calls table does NOT exist in 3CX Professional
# Use WHERE clause on cl_calls: end_time IS NULL OR end_time > NOW()
```

---

### 3.5 Log Parser Module (logs/parser.py)

```python
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
    status: Optional[int] = None  # For responses
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

# Log entry pattern
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

# Routing decision patterns
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
        match = LOG_PATTERN.match(line)
        if not match:
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
        # Check if entry contains SIP method
        for method in SipMethod:
            if method.value in entry.message:
                call_id_match = CALL_ID_PATTERN.search(entry.message)
                from_match = FROM_PATTERN.search(entry.message)
                to_match = TO_PATTERN.search(entry.message)
                response_match = SIP_RESPONSE_PATTERN.search(entry.message)

                return SipMessage(
                    timestamp=entry.timestamp,
                    method=method,
                    call_id=call_id_match.group(1) if call_id_match else "",
                    from_number=from_match.group(1) if from_match else None,
                    to_number=to_match.group(1) if to_match else None,
                    status=int(response_match.group(1)) if response_match else None,
                    raw=entry.message
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
        open_fn = gzip.open if self.log_path.suffix == ".gz" else open

        with open_fn(self.log_path, "rt", encoding=self.encoding) as f:
            for line in f:
                entry = self.parse_line(line)
                if entry:
                    yield entry

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
                results.append(CallLogEntry(
                    timestamp=entry.timestamp,
                    level=entry.level,
                    message=entry.message
                ))
        return results

    def get_errors(self, start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> List[LogEntry]:
        """Get error and warning log entries."""
        errors = []
        for entry in self.iter_entries():
            if entry.level in (LogLevel.ERROR, LogLevel.FATAL, LogLevel.WARN):
                if start_time and entry.timestamp < start_time:
                    continue
                if end_time and entry.timestamp > end_time:
                    continue
                errors.append(entry)
        return errors
```

---

### 3.6 Log Tailing Module (logs/tailer.py)

```python
"""
Real-time log file tailing.

Watches 3CX log files for new entries and streams them as they appear.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional
from .parser import LogParser, LogEntry

@dataclass
class TailConfig:
    """Configuration for log tailing."""
    follow: bool = True
    lines: int = 10  # Initial lines to show
    poll_interval: float = 0.1  # Seconds
    encoding: str = "utf-8"

class LogTailer:
    """Tail a log file in real-time."""

    def __init__(self, log_path: str, config: TailConfig):
        self.log_path = Path(log_path)
        self.config = config
        self.parser = LogParser(str(log_path), config.encoding)
        self._running = False
        self._position = 0

    async def _initial_lines(self) -> list[LogEntry]:
        """Get initial lines from the end of the file."""
        entries = []
        with open(self.log_path, "r", encoding=self.config.encoding) as f:
            lines = f.readlines()
            # Get last N lines
            for line in lines[-self.config.lines:]:
                entry = self.parser.parse_line(line)
                if entry:
                    entries.append(entry)
            self._position = f.tell()
        return entries

    async def tail(self) -> AsyncIterator[LogEntry]:
        """Tail the log file, yielding new entries."""
        # Yield initial lines
        for entry in await self._initial_lines():
            yield entry

        self._running = True

        try:
            while self._running and self.config.follow:
                # Check for new data
                with open(self.log_path, "r", encoding=self.config.encoding) as f:
                    f.seek(self._position)
                    new_data = f.read()

                    if new_data:
                        for line in new_data.splitlines():
                            entry = self.parser.parse_line(line)
                            if entry:
                                yield entry
                        self._position = f.tell()

                await asyncio.sleep(self.config.poll_interval)
        except asyncio.CancelledError:
            self._running = False
            raise

    def stop(self) -> None:
        """Stop tailing."""
        self._running = False

class MultiFileTailer:
    """Tail multiple log files simultaneously."""

    def __init__(self, log_paths: list[str], config: TailConfig):
        self.tailers = [LogTailer(path, config) for path in log_paths]
        self._tasks: list[asyncio.Task] = []

    async def tail_all(self) -> AsyncIterator[tuple[str, LogEntry]]:
        """Tail all log files, yielding (path, entry)."""
        async def tail_file(tailer: LogTailer) -> AsyncIterator[tuple[str, LogEntry]]:
            async for entry in tailer.tail():
                yield (str(tailer.log_path), entry)

        # Create tasks for each tailer
        queues: list[asyncio.Queue] = [asyncio.Queue() for _ in self.tailers]

        async def worker(tailer: LogTailer, queue: asyncio.Queue) -> None:
            async for entry in tailer.tail():
                await queue.put((str(tailer.log_path), entry))

        for tailer, queue in zip(self.tailers, queues):
            task = asyncio.create_task(worker(tailer, queue))
            self._tasks.append(task)

        try:
            # Yield from any queue as entries arrive
            while any(not t.done() for t in self._tasks):
                for queue in queues:
                    try:
                        yield await asyncio.wait_for(queue.get(), timeout=0.1)
                    except asyncio.TimeoutError:
                        continue
        finally:
            for tailer in self.tailers:
                tailer.stop()
            for task in self._tasks:
                task.cancel()
```

---

### 3.7 MCP Tool Specifications

#### Calls Tool (tools/calls.py)

```python
"""
Call-related MCP tools.

Provides call record queries and combined database+log operations.
"""
from mcp.server.fastmcp import FastMCP
from ..database.connection import DatabasePool
from ..logs.parser import LogParser
from ..models.call import CallRecord, CallLogEntry

def register(mcp: FastMCP, db: DatabasePool, log_parser: LogParser):
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
               JOIN cl_participants p ON c.id = p.id
               WHERE p.caller_number ILIKE $1
                  OR p.display_name ILIKE $1
               ORDER BY c.start_time DESC
               LIMIT $2""",
            search_pattern, limit
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
        call = await db.fetchone(
            "SELECT * FROM cl_calls WHERE id = $1 AND is_answered = 'f'",
            call_id
        )

        if not call:
            return {"error": "Call not found or was answered"}

        # Get flow segments
        segments = await db.fetch(
            """SELECT
                   s.seq_order,
                   s.type,
                   src.caller_number as source,
                   dst.caller_number as destination,
                   s.start_time,
                   s.end_time
               FROM cl_segments s
               JOIN cl_participants src ON s.src_part_id = src.id
               JOIN cl_participants dst ON s.dst_part_id = dst.id
               WHERE s.call_id = $1
               ORDER BY s.seq_order""",
            call_id
        )

        # Get party info with failure reasons
        party_info = await db.fetch(
            """SELECT * FROM cl_party_info
               WHERE call_id = $1
               ORDER BY id""",
            call_id
        )

        return {
            "call": call,
            "segments": segments,
            "party_info": party_info,
            "analysis": _analyze_failure(call, segments, party_info)
        }

        Args:
            call_id: The unique call identifier

        Returns:
            Analysis including error messages, routing path, and potential issues.
        """
        call = await db.fetchone(
            "SELECT * FROM calls WHERE CallID = $1 AND Status IN ('failed', 'abandoned')",
            call_id
        )

        if not call:
            return {"error": "Call not found or not failed"}

        log_entries = log_parser.find_by_call_id(call_id)

        # Find errors and warnings
        errors = [
            entry for entry in log_entries
            if entry.message and ("ERROR" in entry.message or "WARN" in entry.message)
        ]

        # Extract routing decisions
        routing_path = [
            entry.routing_decision
            for entry in log_entries
            if entry.routing_decision
        ]

        return {
            "call": call,
            "errors": [
                {"timestamp": e.timestamp.isoformat(), "message": e.message}
                for e in errors
            ],
            "routing_path": [
                {"timestamp": r.timestamp.isoformat(), "decision": r.decision}
                for r in routing_path
            ],
            "analysis": _analyze_failure(call, errors, routing_path)
        }

def _analyze_failure(call: dict, errors: list, routing_path: list) -> str:
    """Analyze failure and provide explanation."""
    if not routing_path:
        return "Call failed before routing - possible trunk or authentication issue."

    last_routing = routing_path[-1]

    if any("no answer" in e.lower() for e in errors):
        return "Call failed due to no answer at destination."

    if any("busy" in e.lower() for e in errors):
        return "Call failed because destination was busy."

    if any("timeout" in e.lower() for e in errors):
        return "Call timed out waiting for answer."

    if any("forbidden" in e.lower() or "unauthorized" in e.lower() for e in errors):
        return "Call failed due to authorization/permission issue."

    return f"Call completed with status: {call.get('Status')}"
```

#### Logs Tool (tools/logs.py)

```python
"""
Log parsing MCP tools.

Provides log file access and parsing capabilities.
"""
from mcp.server.fastmcp import FastMCP
from ..logs.parser import LogParser, LogEntry
from ..logs.tailer import LogTailer, TailConfig
from typing import AsyncIterator

# Global tailer for streaming
_active_tailer: LogTailer | None = None

def register(mcp: FastMCP, log_parser: LogParser):
    """Register log tools."""

    @mcp.tool()
    async def tail_logs(
        follow: bool = False,
        lines: int = 10,
        log_path: str | None = None,
    ) -> list[dict]:
        """Get recent log entries or tail logs in real-time.

        Args:
            follow: If True, continue streaming new entries
            lines: Number of recent lines to show initially
            log_path: Optional custom log path

        Returns:
            List of log entries. If follow=True, streams indefinitely.
        """
        global _active_tailer

        parser = LogParser(log_path) if log_path else log_parser
        config = TailConfig(follow=follow, lines=lines)

        if not follow:
            # Return static entries
            entries = []
            for entry in parser.iter_entries():
                entries.append({
                    "timestamp": entry.timestamp.isoformat(),
                    "level": entry.level.value,
                    "message": entry.message,
                })
                if len(entries) >= lines:
                    break
            return entries[-lines:] if entries else []

        # For streaming, we return a message indicating the tailer is running
        # Real streaming is handled via a separate mechanism
        return {"status": "streaming_started", "message": "Use stream_logs endpoint for real-time updates"}

    @mcp.tool()
    async def query_logs(
        start_date: str,
        end_date: str,
        level: str | None = None,
        filter_text: str | None = None,
    ) -> list[dict]:
        """Query log entries by date range and filters.

        Args:
            start_date: Start datetime (ISO format)
            end_date: End datetime (ISO format)
            level: Filter by log level (DEBUG, INFO, WARN, ERROR)
            filter_text: Text to search for in messages

        Returns:
            Matching log entries.
        """
        from datetime import datetime

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
                "message": entry.message,
            })

        return entries

    @mcp.tool()
    async def get_call_logs(call_id: str) -> list[dict]:
        """Get all log entries for a specific call.

        Args:
            call_id: The unique call identifier

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
            for entry in call_entries
        ]

    @mcp.tool()
    async def get_extension_logs(
        extension: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict]:
        """Get log entries for a specific extension.

        Args:
            extension: Extension number
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Log entries for the extension.
        """
        entries = log_parser.find_by_extension(extension)

        if start_date or end_date:
            from datetime import datetime
            start = datetime.fromisoformat(start_date) if start_date else None
            end = datetime.fromisoformat(end_date) if end_date else None

            entries = [
                e for e in entries
                if (not start or e.timestamp >= start)
                and (not end or e.timestamp <= end)
            ]

        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.value,
                "message": entry.message,
            }
            for entry in entries
        ]

    @mcp.tool()
    async def parse_sip_messages(log_entry_ids: list[str]) -> list[dict]:
        """Parse SIP messages from log entries.

        Args:
            log_entry_ids: List of log entry identifiers (timestamps)

        Returns:
            Parsed SIP messages with method, call-id, from/to numbers.
        """
        # This would work with a different log entry ID system
        # For now, parse recent entries with SIP content
        results = []
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
            if len(results) >= len(log_entry_ids):
                break
        return results

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
    async def get_errors(
        start_date: str,
        end_date: str,
        severity: str | None = None,
    ) -> list[dict]:
        """Get error and warning log entries.

        Args:
            start_date: Start datetime (ISO format)
            end_date: End datetime (ISO format)
            severity: Filter by severity (ERROR, WARN, FATAL)

        Returns:
            Error log entries.
        """
        from datetime import datetime

        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        errors = log_parser.get_errors(start, end)

        if severity:
            errors = [e for e in errors if e.level.value == severity.upper()]

        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "level": e.level.value,
                "message": e.message,
            }
            for e in errors
        ]
```

#### Extensions Tool (tools/extensions.py)

```python
"""
Extension/participant management MCP tools.

Note: 3CX Professional does not have a separate extensions table.
Extension information is stored in cl_participants table.
"""
from mcp.server.fastmcp import FastMCP
from ..database.connection import DatabasePool

def register(mcp: FastMCP, db: DatabasePool):
    """Register extension/participant tools."""

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
```

#### Queues Tool (tools/queues.py)

```python
"""
Queue/ring group management MCP tools.

Note: Queue membership is managed via CDR and audit_log.
Queue definitions are in cl_participants (dn_type=2).
"""
from mcp.server.fastmcp import FastMCP
from ..database.connection import DatabasePool

def register(mcp: FastMCP, db: DatabasePool):
    """Register queue tools."""

    @mcp.tool()
    async def list_queues() -> list[dict]:
        """List all call queues/ring groups.

        Returns:
            List of queues with member counts.
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
            """SELECT
                   time_start,
                   from_displayname as caller,
                   EXTRACT(EPOCH FROM ts_waiting) as wait_seconds,
                   reason_noanswerdesc as reason
               FROM callcent_queuecalls
               WHERE q_num = $1
                 AND call_result = 'ABANDONED'
               ORDER BY time_start DESC
               LIMIT $1""",
            queue_dn, limit
        )
```

#### Audit Tool (tools/audit.py)

```python
"""
Configuration change audit trail MCP tools.
"""
from mcp.server.fastmcp import FastMCP
from ..database.connection import DatabasePool

def register(mcp: FastMCP, db: DatabasePool):
    """Register audit tools."""

    @mcp.tool()
    async def get_audit_log(
        limit: int = 100,
        start_date: str | None = None,
        end_date: str | None = None,
        user_name: str | None = None,
        action: int | None = None,
    ) -> list[dict]:
        """Get configuration change audit trail.

        Args:
            limit: Maximum records to return
            start_date: Start date filter (ISO format)
            end_date: End date filter (ISO format)
            user_name: Filter by user
            action: Filter by action type

        Returns:
            Audit log entries.
        """
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if start_date:
            query += " AND time_stamp >= $1"
            params.append(start_date)

        if end_date:
            query += f" AND time_stamp <= ${len(params) + 1}"
            params.append(end_date)

        if user_name:
            query += f" AND user_name = ${len(params) + 1}"
            params.append(user_name)

        if action:
            query += f" AND action = ${len(params) + 1}"
            params.append(action)

        query += f" ORDER BY time_stamp DESC LIMIT ${len(params) + 1}"
        params.append(limit)

        return await db.fetch(query, *params)

    @mcp.tool()
    async def get_extension_changes(extension_name: str, days: int = 30) -> list[dict]:
        """Get configuration changes for an extension.

        Args:
            extension_name: Extension name or DN
            days: Number of days to look back

        Returns:
            Configuration changes for the extension.
        """
        return await db.fetch(
            """SELECT * FROM audit_log
               WHERE object_name ILIKE $1
                 AND time_stamp >= NOW() - INTERVAL '1 day' * $2
               ORDER BY time_stamp DESC""",
            f"%{extension_name}%", days
        )
```

#### Queues Tool (tools/queues.py)

```python
"""
Queue management MCP tools.

Provides queue CRUD operations and member management.
"""
from mcp.server.fastmcp import FastMCP
from ..database.connection import DatabasePool

def register(mcp: FastMCP, db: DatabasePool):
    """Register queue tools."""

    @mcp.tool()
    async def list_queues() -> list[dict]:
        """List all call queues.

        Returns:
            List of queues with member counts.
        """
        return await db.fetch(
            """SELECT q.*, COUNT(qm.ExtensionNumber) as member_count
               FROM queues q
               LEFT JOIN queue_members qm ON q.Id = qm.QueueId
               GROUP BY q.Id
               ORDER BY q.Name"""
        )

    @mcp.tool()
    async def get_queue(queue_id: int) -> dict | None:
        """Get details of a specific queue including members.

        Args:
            queue_id: The queue ID

        Returns:
            Queue details with members.
        """
        queue = await db.fetchone("SELECT * FROM queues WHERE Id = $1", queue_id)
        if not queue:
            return None

        members = await db.fetch(
            "SELECT * FROM queue_members WHERE QueueId = $1 ORDER BY Priority",
            queue_id
        )

        return {**queue, "members": members}

    @mcp.tool()
    async def create_queue(
        name: str,
        number: str,
        strategy: str = "ringall",
        timeout: int = 30,
        wrap_up_time: int = 0,
    ) -> dict:
        """Create a new call queue.

        Warning: This modifies the 3CX database directly.

        Args:
            name: Queue name
            number: Queue extension number
            strategy: Ring strategy (ringall, hunt, memory, random, fewestcalls,_rrmemory)
            timeout: Ring timeout in seconds
            wrap_up_time: Wrap-up time in seconds

        Returns:
            Created queue record.
        """
        async with db.transaction() as conn:
            result = await conn.fetchrow(
                """INSERT INTO queues (Name, Number, Strategy, Timeout, WrapUpTime)
                   VALUES ($1, $2, $3, $4, $5)
                   RETURNING *""",
                name, number, strategy, timeout, wrap_up_time
            )

            # Audit log
            await conn.execute(
                """INSERT INTO audit_log (action, entity, entity_id, details)
                   VALUES ('create', 'queue', $1, $2)""",
                result["Id"], f"Created queue {name}"
            )

            return dict(result)

    @mcp.tool()
    async def update_queue(
        queue_id: int,
        name: str | None = None,
        timeout: int | None = None,
        strategy: str | None = None,
    ) -> dict:
        """Update queue settings.

        Warning: This modifies the 3CX database directly.

        Args:
            queue_id: The queue ID
            name: New queue name
            timeout: New ring timeout
            strategy: New ring strategy

        Returns:
            Updated queue record.
        """
        # Similar to update_extension
        pass  # Implementation follows same pattern

    @mcp.tool()
    async def add_queue_member(
        queue_id: int,
        extension_number: str,
        priority: int = 0,
        penalty: int = 0,
    ) -> dict:
        """Add an extension to a queue.

        Warning: This modifies the 3CX database directly.

        Args:
            queue_id: The queue ID
            extension_number: Extension number to add
            priority: Ring priority (lower = higher priority)
            penalty: Penalty for overflow conditions

        Returns:
            Queue member record.
        """
        async with db.transaction() as conn:
            result = await conn.fetchrow(
                """INSERT INTO queue_members (QueueId, ExtensionNumber, Priority, Penalty)
                   VALUES ($1, $2, $3, $4)
                   ON CONFLICT (QueueId, ExtensionNumber)
                   DO UPDATE SET Priority = $3, Penalty = $4
                   RETURNING *""",
                queue_id, extension_number, priority, penalty
            )

            # Audit log
            await conn.execute(
                """INSERT INTO audit_log (action, entity, entity_id, details)
                   VALUES ('add_member', 'queue', $1, $2)""",
                queue_id, f"Added extension {extension_number}"
            )

            return dict(result)

    @mcp.tool()
    async def remove_queue_member(queue_id: int, extension_number: str) -> dict:
        """Remove an extension from a queue.

        Warning: This modifies the 3CX database directly.

        Args:
            queue_id: The queue ID
            extension_number: Extension number to remove

        Returns:
            Deleted member record.
        """
        async with db.transaction() as conn:
            result = await conn.fetchrow(
                """DELETE FROM queue_members
                   WHERE QueueId = $1 AND ExtensionNumber = $2
                   RETURNING *""",
                queue_id, extension_number
            )

            if not result:
                raise ValueError(
                    f"Extension {extension_number} not found in queue {queue_id}"
                )

            # Audit log
            await conn.execute(
                """INSERT INTO audit_log (action, entity, entity_id, details)
                   VALUES ('remove_member', 'queue', $1, $2)""",
                queue_id, f"Removed extension {extension_number}"
            )

            return dict(result)
```

#### Trunks Tool (tools/trunks.py)

```python
"""
Trunk management MCP tools.

Provides trunk queries and updates.
"""
from mcp.server.fastmcp import FastMCP
from ..database.connection import DatabasePool

def register(mcp: FastMCP, db: DatabasePool):
    """Register trunk tools."""

    @mcp.tool()
    async def list_trunks() -> list[dict]:
        """List all SIP trunks.

        Returns:
            List of trunks with status.
        """
        return await db.fetch(
            "SELECT * FROM trunks ORDER BY Name"
        )

    @mcp.tool()
    async def get_trunk(trunk_id: int) -> dict | None:
        """Get details of a specific trunk.

        Args:
            trunk_id: The trunk ID

        Returns:
            Trunk details.
        """
        return await db.fetchone(
            "SELECT * FROM trunks WHERE Id = $1",
            trunk_id
        )

    @mcp.tool()
    async def update_trunk(
        trunk_id: int,
        host: str | None = None,
        port: int | None = None,
        enabled: bool | None = None,
    ) -> dict:
        """Update trunk configuration.

        Warning: This modifies the 3CX database directly.

        Args:
            trunk_id: The trunk ID
            host: New SIP host
            port: New SIP port
            enabled: Enable/disable trunk

        Returns:
            Updated trunk record.
        """
        # Implementation follows same pattern as update_extension
        pass
```

---

### 3.8 Main Module (main.py)

```python
"""
3CX Debugging MCP Server - Main Entry Point.

Runs directly on the 3CX server, providing call flow debugging capabilities
without requiring enterprise XAPI licensing.
"""
import asyncio
from mcp.server.fastmcp import FastMCP

from .config import Config
from .database.connection import DatabasePool, DatabaseError
from .logs.parser import LogParser
from .tools import calls, extensions, queues, trunks, logs

def create_mcp_server(config: Config) -> FastMCP:
    """Create and configure the MCP server."""
    mcp = FastMCP(
        config.server.mcp_name,
        json_response=True,
        log_level=config.server.log_level
    )

    # Initialize database connection
    db = DatabasePool(config.database)

    # Initialize log parser
    log_parser = LogParser(config.logs.main_log_path, config.logs.encoding)

    # Register tools
    calls.register(mcp, db, log_parser)
    extensions.register(mcp, db)
    queues.register(mcp, db)
    trunks.register(mcp, db)
    logs.register(mcp, log_parser)

    # Add health check tool
    @mcp.tool()
    async def health_check() -> dict:
        """Check server health and connectivity."""
        try:
            # Test database connection
            await db.fetchval("SELECT 1")
            db_status = "connected"
        except DatabaseError as e:
            db_status = f"error: {e}"

        # Check log file access
        from pathlib import Path
        log_status = "accessible" if Path(config.logs.main_log_path).exists() else "missing"

        return {
            "status": "healthy" if db_status == "connected" else "degraded",
            "database": db_status,
            "logs": log_status,
            "config": {
                "database": config.database.database,
                "log_path": config.logs.main_log_path,
            }
        }

    return mcp, db

async def main():
    """Main entry point."""
    import sys

    # Load configuration
    config = Config.from_env()
    config.validate()

    # Create server
    mcp, db = create_mcp_server(config)

    # Initialize database pool
    await db.initialize()

    try:
        # Run MCP server (stdio transport)
        await mcp.run()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 4. Data Models

### 4.1 Call Record

```python
{
    "CallID": "call-12345",
    "CallerID": "15555551234",
    "CalleeID": "1001",
    "StartTime": "2026-03-06T10:30:00Z",
    "EndTime": "2026-03-06T10:35:00Z",
    "Duration": 300,
    "Status": "completed",
    "Direction": "inbound",
    "TrunkID": "trunk-1",
    "QueueID": null,
    "Extension": "1001"
}
```

### 4.2 Log Entry

```python
{
    "timestamp": "2026-03-06T10:30:00.123Z",
    "level": "INFO",
    "message": "Routing call from trunk-1 to 1001",
    "sip_method": "INVITE",
    "from_number": "15555551234",
    "to_number": "1001",
    "routing_decision": "Routing call from trunk-1 to 1001"
}
```

### 4.3 Call Trace Result

```python
{
    "call": {
        "CallID": "call-12345",
        "CallerID": "15555551234",
        "CalleeID": "1001",
        "StartTime": "2026-03-06T10:30:00Z",
        "EndTime": "2026-03-06T10:35:00Z",
        "Duration": 300,
        "Status": "completed"
    },
    "log_entries": [
        {
            "timestamp": "2026-03-06T10:30:00.100Z",
            "level": "INFO",
            "message": "Received INVITE from trunk-1",
            "sip_method": "INVITE",
            "from_number": "15555551234",
            "to_number": "1001"
        },
        {
            "timestamp": "2026-03-06T10:30:00.200Z",
            "level": "INFO",
            "message": "Routing call from trunk-1 to 1001",
            "routing_decision": "Routing call from trunk-1 to 1001"
        }
    ]
}
```

---

## 5. Security Considerations

### 5.1 Database Access

| Risk | Mitigation |
|------|------------|
| SQL injection | Use parameterized queries exclusively |
| Privilege escalation | Use read-only user for read operations |
| Data corruption | Use transactions for write operations with rollback on error |
| Credential exposure | Store credentials in environment variables, not code |

### 5.2 File Access

| Risk | Mitigation |
|------|------------|
| Log file tampering | Read-only access to log files |
| Path traversal | Validate all file paths against allowed directories |
| DoS via large logs | Limit log read operations with timeout and size limits |

### 5.3 Write Operations

| Risk | Mitigation |
|------|------------|
| Accidental modification | Optional write disable flag (ENABLE_WRITES=false) |
| Data corruption | Audit log for all write operations |
| Race conditions | Use database transactions |

---

## 6. Deployment

### 6.1 Installation

```bash
# Install on 3CX server
cd /opt
git clone https://github.com/your-repo/3cx-mcp-debugging.git
cd 3cx-mcp-debugging
pip install -r requirements.txt
```

### 6.2 Configuration

```bash
# Create .env file
cat > /opt/3cx-mcp-debugging/.env << EOF
DB_NAME=3cxpbx
DB_USER=3cxpbx
DB_PASSWORD=from_3cx_config
DB_USE_SOCKET=true
DB_SOCKET_DIR=/var/run/postgresql
LOG_PATH=/var/lib/3cxpbx/Bin/3CXPhoneSystem.log
MCP_NAME=3cx-debugging
ENABLE_WRITES=true
EOF
```

### 6.3 Systemd Service

```ini
# /etc/systemd/system/3cx-mcp-debugging.service
[Unit]
Description=3CX Debugging MCP Server
After=network.target postgresql.service

[Service]
Type=simple
User=3cxpbx
WorkingDirectory=/opt/3cx-mcp-debugging
EnvironmentFile=/opt/3cx-mcp-debugging/.env
ExecStart=/usr/bin/python -m src.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
systemctl enable 3cx-mcp-debugging
systemctl start 3cx-mcp-debugging
```

### 6.4 MCP Client Configuration (Claude Desktop)

```json
{
  "mcpServers": {
    "3cx-debugging": {
      "command": "ssh",
      "args": [
        "user@3cx-server",
        "cd /opt/3cx-mcp-debugging && python -m src.main"
      ],
      "env": {}
    }
  }
}
```

Or for local MCP server:

```json
{
  "mcpServers": {
    "3cx-debugging": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "/opt/3cx-mcp-debugging",
      "env": {
        "DB_NAME": "3cxpbx",
        "DB_USE_SOCKET": "true",
        "LOG_PATH": "/var/lib/3cxpbx/Bin/3CXPhoneSystem.log"
      }
    }
  }
}
```

---

## 7. Dependencies

```
mcp>=0.9.0
asyncpg>=0.29.0      # Async PostgreSQL driver
pydantic>=2.5.0
python-dotenv>=1.0.0
watchfiles>=0.21.0   # For file watching (optional)
```

---

## 8. Database Schema (Verified)

Based on actual 3CX v20.0.8 Professional backup:

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `cl_calls` | Call summary | `id`, `start_time`, `end_time`, `is_answered`, `ringing_dur`, `talking_dur`, `q_wait_dur` |
| `cl_participants` | Participants | `id`, `dn_type`, `dn`, `caller_number`, `display_name`, `did_number` |
| `cl_segments` | Call flow | `call_id`, `seq_order`, `src_part_id`, `dst_part_id`, `type`, `start_time`, `end_time` |
| `cl_party_info` | Party details | `call_id`, `role`, `is_inbound`, `end_status`, `billing_cost` |
| `cdroutput` | Full CDR | `cdr_id`, `source_*`, `destination_*`, `creation_method`, `termination_reason` |
| `recordings` | Recordings | `id_recording`, `recording_url`, `start_time`, `sentiment_score`, `cdr_id` |
| `s_voicemail` | Voicemail | `idcallcent_queuecalls`, `caller`, `callee`, `heard`, `transcription` |
| `callcent_queuecalls` | Queue stats | `q_num`, `time_start`, `ts_waiting`, `call_result` |
| `audit_log` | Audit trail | `time_stamp`, `user_name`, `action`, `object_name`, `prev_data`, `new_data` |
| `cl_quality` | Quality metrics | `call_id`, `a_codec`, `b_codec`, `a_mos_from_pbx`, `b_mos_from_pbx` |

### Key Queries

```sql
-- Active calls
SELECT * FROM cl_calls
WHERE end_time IS NULL OR end_time > NOW()
ORDER BY start_time DESC;

-- Call flow path
SELECT s.seq_order, src.caller_number, dst.caller_number, s.type
FROM cl_segments s
JOIN cl_participants src ON s.src_part_id = src.id
JOIN cl_participants dst ON s.dst_part_id = dst.id
WHERE s.call_id = ?;

-- Failed calls
SELECT * FROM cl_calls
WHERE is_answered = 'f'
ORDER BY start_time DESC;

-- Participants by type
SELECT * FROM cl_participants
WHERE dn_type = 0;  -- 0=extension, 1=external, 2=queue, 5=voicemail

-- Queue statistics
SELECT
    q_num as queue_number,
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE call_result = 'ANSWERED') as answered,
    COUNT(*) FILTER (WHERE call_result = 'ABANDONED') as abandoned,
    AVG(EXTRACT(EPOCH FROM ts_waiting)) as avg_wait_seconds
FROM callcent_queuecalls
WHERE time_start >= NOW() - INTERVAL '7 days'
GROUP BY q_num;

-- CDR with routing path
SELECT * FROM cdroutput
WHERE call_history_id = ?
ORDER BY cdr_started_at;
```

---

## 9. Implementation Phases (Updated)

| Phase | Status | Description | Deliverables |
|-------|--------|-------------|--------------|
| **Phase 1** | ✅ Complete | Database discovery & schema documentation | Schema docs created in `docs/schema/` |
| **Phase 2** | Pending | Log file format documentation | Log patterns, SIP message formats |
| **Phase 3** | Pending | Database connection layer | Connection pool, basic queries |
| **Phase 4** | Pending | Log parser | Parse entries, extract SIP messages |
| **Phase 5** | Pending | MCP read tools | List/get calls, participants, queue stats |
| **Phase 6** | Pending | Hybrid tools | get_call_flow, debug_failed_call |
| **Phase 7** | Pending | Log streaming tools | tail_logs, real-time updates |
| **Phase 8** | Pending | Write tools | Configuration tracking only (no direct DB writes) |
| **Phase 9** | Pending | Testing & validation | Test on actual 3CX Professional instance |
| **Phase 10** | Pending | Documentation & deployment | User docs, installation guide |

---

## 10. Remaining Open Questions

1. **Credentials**: Where are database credentials stored in 3CX Professional? (Need to locate)
2. **Log Format**: What is the exact format of 3CX log entries? (Need to verify on server)
3. **Write Safety**: Can database writes be safely made? (Recommend: Read-only for safety, audit_log for tracking)
4. **Real-time Updates**: Use PostgreSQL LISTEN/NOTIFY or log tailing? (Test both)
5. **Rotated Logs**: How are log files rotated and named? (Need to verify)
6. **Schema Version**: Does the schema vary between 3CX versions? (Likely yes, need version detection)

---

## 11. Key Schema Differences from Assumptions

| Original Assumption | Actual Schema | Impact |
|---------------------|---------------|--------|
| Table `Calls` | `cl_calls` | Update all queries |
| Column `CallID` | `id` (integer) | Use integer IDs |
| Column `CallerID` | Not a direct column | Join via `cl_participants` |
| Table `ActiveCalls` | Does not exist | Use WHERE clause |
| Booleans `true/false` | Booleans `t/f` | PostgreSQL style |
| Duration as integer | INTERVAL type | Parse `HH:MM:SS.mmmmmm` |
| Table `Extensions` | `cl_participants` (dn_type=0) | Use participants table |
| Table `Queues` | `cl_participants` (dn_type=2) | Use participants table |

| Aspect | XAPI Client | Debugging Add-On |
|--------|-------------|------------------|
| **License** | Enterprise only | Professional compatible |
| **Access Method** | REST API + OAuth2 | Direct database + file access |
| **Authentication** | Client credentials | PostgreSQL auth |
| **Real-time** | Polling XAPI | Log tailing / DB LISTEN |
| **Write Safety** | Official API | Direct DB (riskier) |
| **Features** | Full CRUD | Full CRUD + detailed logs |
| **Installation** | Any network | Must run on 3CX server |