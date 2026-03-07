# 3CX Debugging MCP Server

Model Context Protocol server for 3CX VoIP server debugging. Enables Claude Code and other LLMs to debug call flow issues by directly accessing 3CX database and log files.

## Overview

This MCP server runs directly on a 3CX server and exposes call flow debugging capabilities as MCP tools. It uses direct database access and log file parsing—no XAPI licensing required. Works with 3CX Professional edition.

Available tool categories:

- **Call Records** - Query calls, trace flow, debug failures, get statistics
- **Participants** - Extension, queue, and trunk participant lookups
- **Queues** - Queue statistics, abandoned calls, SLA metrics
- **Logs** - Parse and search 3CX log files for SIP messages
- **Audit** - Configuration change history from audit log

## Requirements

- 3CX Version 20+ (Professional edition compatible)
- Direct PostgreSQL database access
- Access to 3CX log files
- Python 3.10+
- Runs on the 3CX server itself

## Installation

```bash
pipx install git+https://github.com/btafoya/3cx-mcp.git
```

Or for local development:

```bash
pipx install .
```

## Configuration

Set environment variables:

```bash
export DB_NAME=3cxpbx
export DB_USER=3cxpbx
export DB_PASSWORD=your-db-password
export DB_SOCKET_DIR=/var/run/postgresql
export LOG_PATH=/var/lib/3cxpbx/Bin/3CXPhoneSystem.log
```

### Environment Variables

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

## Usage

### Running the MCP Server

After installation with pipx:

```bash
3cx-mcp
```

Or:

```bash
3cx-debug-mcp
```

For development without installation:

```bash
python -m src
```

### Claude Code CLI Configuration

Install the MCP server in one command:

```bash
claude mcp add --transport stdio \
  --env DB_NAME=3cxpbx \
  --env DB_USER=3cxpbx \
  --env DB_PASSWORD=your-db-password \
  --env LOG_PATH=/var/lib/3cxpbx/Bin/3CXPhoneSystem.log \
  3cx-debug -- 3cx-mcp
```

**Important:** This server must run on the 3CX server itself because it requires:
- Direct PostgreSQL database access (via Unix socket)
- Filesystem access to 3CX log files

For more options, see the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).

## Available MCP Tools

### System Tools

| Tool | Description |
|------|-------------|
| `health_check` | Check server health and connectivity |
| `get_database_info` | Get database version and available tables |
| `server_info` | Get server information and configuration |

### Call Tools

| Tool | Description |
|------|-------------|
| `list_calls` | List call records with filtering and pagination |
| `get_call_details` | Get full details of a specific call |
| `get_active_calls` | Get all currently active calls |
| `get_call_flow` | Get complete call flow path with segments |
| `get_call_statistics` | Get call statistics for a date range |
| `search_calls` | Search call records by participant info |
| `trace_call` | Get complete call trace combining database and logs |
| `debug_failed_call` | Debug a failed call to identify root cause |
| `get_failed_calls` | Get list of failed calls |
| `get_cdr_by_call_history` | Get CDR entries for a call history ID |

### Participant Tools

| Tool | Description |
|------|-------------|
| `get_participant` | Get participant details by ID |
| `search_participants` | Search participants by number or name |
| `get_extension_participants` | Get participants for a specific extension |
| `get_queue_participants` | Get participants for a specific queue |
| `get_trunk_participants` | Get participants for a specific trunk |

### Queue Tools

| Tool | Description |
|------|-------------|
| `get_queue_statistics` | Get queue statistics for a date range |
| `get_abandoned_calls` | Get abandoned queue calls |
| `get_queue_sla` | Get SLA compliance metrics |
| `get_agent_performance` | Get agent performance statistics |

### Log Tools

| Tool | Description |
|------|-------------|
| `search_logs` | Search log files for a pattern |
| `get_call_logs` | Get log entries for a specific call |
| `get_error_logs` | Get recent error log entries |
| `get_sip_messages` | Extract SIP messages for a call |

### Audit Tools

| Tool | Description |
|------|-------------|
| `get_audit_log` | Get audit log entries |
| `get_config_changes` | Get configuration changes for a period |
| `get_user_activity` | Get user activity from audit log |

## Database Access

The server uses PostgreSQL's Unix socket for connection (default: `/var/run/postgresql`). This is the preferred method for connections from the same host as the database.

When using socket authentication (default):
- No password required if configured with `peer` or `trust` auth
- Set `DB_USE_SOCKET=false` to use TCP with password authentication

## Documentation

- [Project Documentation](./CLAUDE.md) - Architecture and development notes
- [Design Document](./DESIGN-debugging-add-on.md) - Database + log parsing architecture
- [Requirements](./REQUIREMENTS-debugging-add-on.md) - Feature requirements specification

### Database Schema Documentation
- [Schema Index](./docs/schema/INDEX.md) - Quick reference and key queries
- [Schema Overview](./docs/schema/README.md) - Database structure summary
- [Call Tables](./docs/schema/call-tables.md) - `cl_calls`, `cl_participants`, `cl_segments`, `cl_party_info`
- [CDR Tables](./docs/schema/cdr-tables.md) - `cdroutput` and related tables
- [Media Tables](./docs/schema/media-tables.md) - Recordings, voicemail, queue statistics
- [Config Tables](./docs/schema/config-tables.md) - `audit_log` and system configuration
- [Other Tables](./docs/schema/other-tables.md) - Quality metrics, chat, meetings, CRM

## Resources

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)

## Development

### Project Structure

```
3cx-mcp/
├── src/
│   ├── __init__.py         # Main entry point
│   ├── config.py           # Configuration management
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
├── CLAUDE.md
├── pyproject.toml
└── README.md
```

### Component Overview

| Module | Purpose |
|--------|---------|
| `config.py` | Configuration from environment variables |
| `database/connection.py` | Async PostgreSQL connection pool |
| `logs/parser.py` | 3CX log file parser with SIP message extraction |
| `tools/calls.py` | Call queries, flow tracing, failure debugging |
| `tools/participants.py` | Extension/queue/trunk queries |
| `tools/queues.py` | Queue statistics and call center analytics |
| `tools/logs.py` | Log file queries and error extraction |
| `tools/audit.py` | Configuration change audit trail |

## License

MIT License

## Contributing

Contributions are welcome. Please ensure:
- Code follows the project's quality standards
- All tests pass
- Documentation is updated

## Security Notes

- Store database credentials in environment variables, not in code
- The server runs on localhost via Unix socket by default
- Limit write operations by setting `ENABLE_WRITES=false` if needed