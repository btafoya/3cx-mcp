# 3CX Debugging MCP Server - Project Documentation

## Project Overview

**Goal:** Build an MCP server that enables Claude Code and other LLMs to debug 3CX call flow issues by directly accessing the PostgreSQL database and log files on the 3CX server.

**Status:** Implemented

**Architecture:**
- Runs directly on 3CX server
- Uses direct PostgreSQL database access (no XAPI required)
- Parses 3CX log files for SIP message tracing
- Exposes debugging tools via MCP protocol

## Architecture

### Technology Stack
- **Language:** Python 3.10+
- **MCP SDK:** FastMCP (`fastmcp>=0.9.0`)
- **Database:** asyncpg for async PostgreSQL access
- **Logs:** Custom parser for 3CX log files
- **Edition:** 3CX Professional (Linux)

### Project Structure
```
3cx-mcp/
├── src/
│   ├── __init__.py         # Main entry point
│   ├── config.py           # Configuration from environment variables
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py   # PostgreSQL connection pool
│   ├── logs/
│   │   ├── __init__.py
│   │   └── parser.py       # Log file parser
│   └── tools/
│       ├── __init__.py
│       ├── calls.py        # Call record tools
│       ├── participants.py # Participant/extension tools
│       ├── queues.py       # Queue statistics tools
│       ├── logs.py         # Log parsing tools
│       └── audit.py        # Audit log tools
├── docs/schema/            # Database schema documentation
├── DESIGN-debugging-add-on.md
├── REQUIREMENTS-debugging-add-on.md
├── pyproject.toml
└── README.md
```

## Database Tables Used

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

## MCP Tools

### System Tools
- `health_check()` - Check server health and connectivity
- `get_database_info()` - Get database version and available tables
- `server_info()` - Get server information and configuration

### Call Tools
- `list_calls()` - List call records with filtering and pagination
- `get_call_details(call_id)` - Get full details of a specific call
- `get_active_calls()` - Get all currently active calls
- `get_call_flow(call_id)` - Get complete call flow path with segments
- `get_call_statistics(start_date, end_date, group_by)` - Get call statistics
- `search_calls(query, limit)` - Search call records by participant info
- `trace_call(call_id)` - Get complete call trace combining database and logs
- `debug_failed_call(call_id)` - Debug a failed call to identify root cause
- `get_failed_calls(limit, start_date)` - Get list of failed calls
- `get_cdr_by_call_history(call_history_id)` - Get CDR entries for a call history ID

### Participant Tools
- `get_participant(participant_id)` - Get participant details by ID
- `search_participants(query, limit)` - Search participants by number or name
- `get_extension_participants(extension)` - Get participants for a specific extension
- `get_queue_participants(queue_number)` - Get participants for a specific queue
- `get_trunk_participants(trunk_number)` - Get participants for a specific trunk

### Queue Tools
- `get_queue_statistics(start_date, end_date, queue_number)` - Get queue statistics
- `get_abandoned_calls(limit, start_date, queue_number)` - Get abandoned queue calls
- `get_queue_sla(start_date, end_date, queue_number, sla_seconds)` - Get SLA compliance
- `get_agent_performance(start_date, end_date, extension)` - Get agent performance

### Log Tools
- `search_logs(pattern, limit)` - Search log files for a pattern
- `get_call_logs(call_id)` - Get log entries for a specific call
- `get_error_logs(limit)` - Get recent error log entries
- `get_sip_messages(call_id)` - Extract SIP messages for a call

### Audit Tools
- `get_audit_log(limit, start_date, end_date)` - Get audit log entries
- `get_config_changes(start_date, end_date)` - Get configuration changes
- `get_user_activity(user_name, start_date, end_date)` - Get user activity

## Configuration

Environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_NAME` | No | 3cxpbx | PostgreSQL database name |
| `DB_USER` | No | 3cxpbx | Database user |
| `DB_PASSWORD` | Yes (if not using socket) | - | Database password |
| `DB_HOST` | No | localhost | Database host |
| `DB_PORT` | No | 5432 | Database port |
| `DB_SOCKET_DIR` | No | /var/run/postgresql | Unix socket directory |
| `DB_USE_SOCKET` | No | true | Use Unix socket instead of TCP |
| `LOG_PATH` | No | /var/lib/3cxpbx/Bin/3CXPhoneSystem.log | Main 3CX log file |
| `LOG_DIR` | No | /var/lib/3cxpbx/Bin | Log directory |
| `MCP_NAME` | No | 3cx-debugging | MCP server name |
| `ENABLE_WRITES` | No | true | Enable write operations |

## Database Access

The server uses PostgreSQL's Unix socket by default for local connections. This is preferred because:
- No password required if `peer` or `trust` authentication is configured
- Faster than TCP for local connections
- More secure for same-host access

Set `DB_USE_SOCKET=false` to use TCP authentication instead.

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the MCP server
python -m src

# Run with pipx after installation
3cx-mcp
```

## Documentation

- [README.md](./README.md) - User documentation
- [DESIGN-debugging-add-on.md](./DESIGN-debugging-add-on.md) - Architecture and design
- [REQUIREMENTS-debugging-add-on.md](./REQUIREMENTS-debugging-add-on.md) - Feature requirements
- [docs/schema/](./docs/schema/) - Database schema documentation

## Code Quality Standards

### Naming Conventions
- Be specific: `user_preferences` not `data`, `extension_config` not `result`
- Functions should describe action + object: `fetch_extensions()` not `get_data()`
- Classes should describe responsibility: `DatabasePool` not `Manager`

### Documentation
- Document why, not what
- Skip comments for self-evident code
- Focus on public APIs and complex logic
- Use docstrings for functions, not inline comments

### Structure
- Prefer simple solutions over complex ones
- Remove abstraction layers that don't serve a purpose
- Keep functions focused on one responsibility

## Writing Standards

### Voice
- Use straight quotes (`"`) not curly quotes
- Vary sentence structure and length
- Be direct: lead with the point, skip preambles
- Use specific examples over vague claims

### Phrases to Avoid
- "delve into" → "examine" or delete
- "in today's fast-paced world" → delete
- "it's important to note that" → delete
- "in order to" → "to"
- "has the ability to" → "can"
- "leverage" → "use"

## Session Notes

### 2026-03-07
- README updated to reflect actual implementation (database access, not XAPI)
- CLAUDE.md rewritten to describe debugging add-on
- XAPI-related configuration variables removed from documentation
- Project correctly documented as 3CX Professional debugging add-on

### 2026-03-04
- Initial project documentation created
- Database schema documentation added
- Design document for debugging add-on created
- Skills incorporated: humanizer, anti-slop