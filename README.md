# 3CX MCP Client

Model Context Protocol client for 3CX VoIP server. Enables Claude Code and other LLMs to interact with 3CX through its Configuration REST API (XAPI).

## Overview

This MCP client exposes 3CX API functionality as MCP tools, allowing LLMs to manage:

- **Departments (Groups)** - Create, update, delete, query departments
- **Users** - User account management, bulk operations, phone management
- **Shared Parking** - Configure call parking slots
- **Live Chat Links** - Manage 3CX live chat URLs
- **System Info** - Version, health checks, system settings
- **AI Settings** - Vector stores, AI resources, templates
- **Backups** - Create, list, restore system backups
- **Activity Logs** - Query system event logs
- **Active Calls** - View and manage ongoing calls
- **Contacts** - Contact directory management
- **Blocklists** - IP and phone number blocking

## Requirements

- 3CX Version 20+
- 8SC and higher ENT/AI or ENT+ license
- Python 3.10+
- Service Principal configured in 3CX

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
export THREECX_SERVER_URL=https://pbx.example.com
export THREECX_CLIENT_ID=your-client-id
export THREECX_CLIENT_SECRET=your-api-key
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `THREECX_SERVER_URL` | Yes | - | 3CX server URL (e.g., https://pbx.example.com) |
| `THREECX_PORT` | No | 5001 | Port number |
| `THREECX_CLIENT_ID` | Yes | - | Service Principal client ID (DN) |
| `THREECX_CLIENT_SECRET` | Yes | - | Service Principal API key |
| `THREECX_VERIFY_SSL` | No | true | Verify SSL certificates |

### Service Principal Setup

1. Go to 3CX Web Client > Integrations > API
2. Press "Add" to create a new client application
3. Specify the Client ID (DN for accessing the route point)
4. Check "XAPI Access Enabled" checkbox
5. Specify Department and Role for appropriate access level
6. System Owner/System Admin grants system-wide rights
7. Save the API key (client_secret) - shown only once

**Important:**
- Only one access token can be created at a time per Service Principal
- The API key is shown only once after creation
- Use a backup or separate PBX instance for testing

## Usage

### Running the MCP Client

After installation with pipx:

```bash
3cx-mcp
```

For development without installation:

```bash
python -m src.main
```

### Claude Desktop Configuration

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "3cx-debug": {
      "command": "3cx-mcp",
      "env": {
        "THREECX_DB_NAME": "3cxpbx",
        "THREECX_DB_USER": "postgres",
        "THREECX_DB_PASSWORD": "your-db-password",
        "THREECX_LOG_PATH": "/var/lib/3cxpbx/Instance1/Logs/3CXPhoneSystem.log"
      }
    }
  }
}
```

**Note:** The debugging add-on runs directly on the 3CX server and requires:
- Direct PostgreSQL database access
- Access to 3CX log files
- No XAPI licensing required (Professional edition compatible)

## Available MCP Tools

### System Tools

| Tool | Description |
|------|-------------|
| `get_system_info` | Get 3CX version and verify connectivity |

### Department Tools

| Tool | Description |
|------|-------------|
| `list_departments` | List all departments with optional member expansion |
| `create_department` | Create a new department |
| `get_department` | Get department details |
| `update_department` | Update department settings |
| `delete_department` | Delete a department |
| `department_exists` | Check if a department name exists |
| `get_department_members` | List members of a department |

### User Tools

| Tool | Description |
|------|-------------|
| `list_users` | List users with pagination and filtering |
| `create_user` | Create a new user account |
| `get_user` | Get user details |
| `update_user` | Update user settings |
| `delete_users` | Delete multiple users |
| `user_exists` | Check if user email exists |
| `find_user_by_email` | Find user by email address |
| `get_first_available_extension` | Get next available extension number |

### Parking Tools

| Tool | Description |
|------|-------------|
| `list_parking` | List all shared parking slots |
| `create_parking` | Create a shared parking slot |
| `get_parking_by_number` | Get parking slot by number |
| `delete_parking` | Delete a parking slot |

### Live Chat Tools

| Tool | Description |
|------|-------------|
| `link_exists` | Check if live chat link exists |
| `validate_link` | Validate a friendly URL |
| `create_link` | Create a live chat link |

## API Capabilities

### OData Query Support

All list endpoints support OData query parameters:

- `$filter` - Filter results
- `$top` - Limit results (pagination)
- `$skip` - Skip records (pagination)
- `$expand` - Expand related entities
- `$select` - Specify fields to return
- `$orderby` - Sort order
- `$search` - Full-text search

### Additional XAPI Endpoints

The 3CX XAPI also provides access to:

- **Active Calls** - View and drop ongoing calls
- **Activity Log** - Query system events
- **AI Settings** - Vector stores and AI resources
- **Backups** - Create and restore backups
- **Blocklist** - IP address blocking
- **Call History** - Call records and reports
- **Contacts** - Contact directory
- **Conference Settings** - MCU configuration
- **Voicemail Settings** - Voicemail configuration

See [3CX API Reference](./3cx-API.md) for complete endpoint documentation.

## Documentation

### Main Documentation
- [3CX API Reference](./3cx-API.md) - Complete API documentation
- [Project Documentation](./CLAUDE.md) - Architecture and development notes
- [Design Document](./DESIGN.md) - System architecture and component design

### Debugging Add-On (Professional Edition)

The **Debugging Add-On** provides call flow debugging capabilities for 3CX Professional without requiring enterprise XAPI licensing. It runs directly on the 3CX server using direct database access and log file parsing.

- [Quick Start Guide](./DEBUGGING-ADD-ON.md) - Installation and usage instructions
- [Requirements](./REQUIREMENTS-debugging-add-on.md) - Feature requirements specification
- [Design](./DESIGN-debugging-add-on.md) - Database + log parsing architecture

### Database Schema Documentation
- [Schema Index](./docs/schema/INDEX.md) - Quick reference and key queries
- [Schema Overview](./docs/schema/README.md) - Database structure summary
- [Call Tables](./docs/schema/call-tables.md) - `cl_calls`, `cl_participants`, `cl_segments`, `cl_party_info`
- [CDR Tables](./docs/schema/cdr-tables.md) - `cdroutput` and related tables
- [Media Tables](./docs/schema/media-tables.md) - Recordings, voicemail, queue statistics
- [Config Tables](./docs/schema/config-tables.md) - `audit_log` and system configuration
- [Other Tables](./docs/schema/other-tables.md) - Quality metrics, chat, meetings, CRM

### Debugging Add-On
- [Requirements](./REQUIREMENTS-debugging-add-on.md) - Call flow debugging requirements
- [Design](./DESIGN-debugging-add-on.md) - Database + log parsing architecture (Professional edition)

## Resources

- [3CX Configuration API Documentation](https://www.3cx.com/docs/configuration-rest-api/)
- [3CX XAPI Tutorial (GitHub)](https://github.com/3cx/xapi-tutorial)
- [OpenAPI Specification](https://raw.githubusercontent.com/3cx/xapi-tutorial/master/swagger.yaml)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

## Development

### Project Structure

```
3cx-mcp/
├── src/
│   ├── __init__.py         # Debugging add-on main entry point
│   ├── config.py           # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py   # PostgreSQL connection pool
│   │   └── schema.py       # Database schema models
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
├── requirements-debugging.txt  # Debugging add-on dependencies
├── DEBUGGING-ADD-ON.md     # Quick start guide
├── REQUIREMENTS-debugging-add-on.md  # Feature requirements
├── DESIGN-debugging-add-on.md       # Architecture design
├── docs/schema/            # Database schema documentation
├── DESIGN.md
├── 3cx-API.md
├── CLAUDE.md
└── README.md
```

### Debugging Add-On Structure

The debugging add-on has its own source structure for running directly on 3CX Professional:

| Module | Purpose |
|--------|---------|
| `config.py` | Configuration from environment variables |
| `database/connection.py` | Async PostgreSQL connection pool |
| `database/schema.py` | Dataclass models for all 3CX tables |
| `logs/parser.py` | 3CX log file parser with SIP message extraction |
| `tools/calls.py` | Call queries, flow tracing, failure debugging |
| `tools/participants.py` | Extension/queue/trunk queries |
| `tools/queues.py` | Queue statistics and call center analytics |
| `tools/logs.py` | Log file queries and error extraction |
| `tools/audit.py` | Configuration change audit trail |

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_client.py
```

## License

This project is provided as-is for use with 3CX VoIP systems.

## Contributing

Contributions are welcome. Please ensure:
- Code follows the project's quality standards
- All tests pass
- Documentation is updated

## Security Notes

- Store API credentials in environment variables, not in code
- Use HTTPS connections in production
- Verify SSL certificates unless using self-signed certs in a trusted environment
- The API key is shown only once - store it securely