# 3CX Debugging Add-On - Quick Start

The 3CX Debugging Add-On is an MCP server that runs directly on the 3CX Professional server to provide call flow debugging capabilities without requiring enterprise XAPI licensing.

## Architecture

- **Database Access**: Direct PostgreSQL connection to 3CX database
- **Log Parsing**: Reads 3CX system logs for detailed call flow tracing
- **MCP Server**: Exposes tools for Claude Code integration

## Installation

On your 3CX server, first ensure pipx is installed:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Then clone and install:

```bash
cd /opt
git clone https://github.com/your-repo/3cx-mcp.git
cd 3cx-mcp
pipx install .
```

## Configuration

Set environment variables:

```bash
export DB_NAME=3cxpbx
export DB_USER=3cxpbx
export DB_USE_SOCKET=true
export DB_SOCKET_DIR=/var/run/postgresql
export LOG_PATH=/var/lib/3cxpbx/Bin/3CXPhoneSystem.log
export MCP_NAME=3cx-debugging
```

## Running the Server

After installation with pipx:

```bash
3cx-mcp
```

For development without installation:

```bash
python -m src
```

## MCP Tools

### Call Tools
- `list_calls` - List call records with filtering
- `get_call_details` - Get full details of a specific call
- `get_active_calls` - Get all currently active calls
- `get_call_flow` - Get complete call flow path
- `get_call_statistics` - Get call statistics for a date range
- `search_calls` - Search call records by participant info
- `trace_call` - Get complete call trace
- `debug_failed_call` - Debug a failed call
- `get_failed_calls` - Get list of failed calls

### Participant Tools
- `list_participants` - List all participants (extensions, trunks, queues)
- `get_participant` - Get details of a specific participant
- `get_extensions_only` - Get list of extensions only
- `get_queues` - Get list of ring groups/queues
- `get_participant_by_dn` - Get participant by DN number
- `search_participants` - Search participants by display name or caller number

### Queue Tools
- `list_queues` - List all call queues/ring groups
- `get_queue_stats` - Get queue statistics for a time period
- `get_queue_abandoned_calls` - Get abandoned calls for a queue
- `get_all_queues_stats` - Get statistics for all queues
- `get_call_center_summary` - Get overall call center statistics

### Log Tools
- `tail_logs` - Get recent log entries
- `query_logs` - Query log entries by date range and filters
- `get_call_logs` - Get all log entries for a specific call
- `get_extension_logs` - Get log entries for a specific extension
- `get_errors` - Get error and warning log entries
- `get_routing_decisions` - Get routing decisions for a call
- `parse_sip_messages` - Parse SIP messages from log entries

### Audit Tools
- `get_audit_log` - Get audit log entries with filtering
- `get_recent_changes` - Get recent configuration changes
- `get_user_changes` - Get changes made by a specific user
- `get_object_changes` - Get changes for a specific object
- `get_extension_changes` - Get configuration changes for a specific extension

### System Tools
- `health_check` - Check server health and connectivity
- `get_database_info` - Get database version and available tables
- `server_info` - Get server information and configuration

## Claude Desktop Configuration

For local MCP server (with pipx):

```json
{
  "mcpServers": {
    "3cx-debugging": {
      "command": "3cx-mcp",
      "env": {
        "DB_NAME": "3cxpbx",
        "DB_USE_SOCKET": "true",
        "LOG_PATH": "/var/lib/3cxpbx/Bin/3CXPhoneSystem.log"
      }
    }
  }
}
```

For remote 3CX server via SSH:

```json
{
  "mcpServers": {
    "3cx-debugging": {
      "command": "ssh",
      "args": [
        "user@3cx-server",
        "3cx-mcp"
      ],
      "env": {}
    }
  }
}
```

## Database Schema

The add-on connects to these 3CX tables:

| Table | Purpose |
|-------|---------|
| `cl_calls` | Call summary records |
| `cl_participants` | Call participants (extensions, trunks, queues) |
| `cl_segments` | Call flow segments (routing steps) |
| `cl_party_info` | Detailed party info with billing |
| `cdroutput` | Full CDR with complete routing path |
| `recordings` | Call recording metadata |
| `s_voicemail` | Voicemail messages |
| `callcent_queuecalls` | Queue call statistics |
| `audit_log` | Configuration change audit trail |
| `cl_quality` | Call quality metrics |

## Key Queries

### Active Calls
```sql
SELECT * FROM cl_calls
WHERE end_time IS NULL OR end_time > NOW()
ORDER BY start_time DESC;
```

### Call Flow Path
```sql
SELECT s.seq_order, src.caller_number, dst.caller_number, s.type
FROM cl_segments s
JOIN cl_participants src ON s.src_part_id = src.id
JOIN cl_participants dst ON s.dst_part_id = dst.id
WHERE s.call_id = ?;
```

### Failed Calls
```sql
SELECT * FROM cl_calls
WHERE is_answered = 'f'
ORDER BY start_time DESC;
```

## Next Steps

1. Verify database credentials on your 3CX server
2. Test database connectivity
3. Verify log file format and location
4. Test tools with Claude Desktop