# 3CX-MCP - Model Context Protocol Client for 3CX VoIP

## Project Overview

**Goal:** Build an MCP (Model Context Protocol) client that enables Claude Code and other LLMs to interact with 3CX VoIP server through its Configuration REST API (XAPI).

**Status:** Early Planning Phase

**Architecture Overview:**
- The MCP client runs as a server component (per MCP spec) that exposes 3CX API functionality as MCP tools
- The client handles OAuth2 authentication and token management for the 3CX API
- LLMs invoke MCP tools which the client translates to 3CX XAPI calls

## Architecture

### Technology Stack
- **Language:** Python
- **MCP SDK:** https://github.com/modelcontextprotocol/python-sdk
- **Target API:** 3CX Configuration REST API (XAPI)
- **HTTP Client:** `httpx` for async requests
- **Auth:** OAuth2 client_credentials flow

### Planned Structure
```
3cx-mcp/
├── src/
│   ├── __init__.py
│   ├── main.py            # MCP server entry point (FastMCP)
│   ├── auth.py            # OAuth2 token management
│   ├── client.py          # 3CX XAPI client wrapper
│   └── tools/             # MCP tool implementations
│       ├── __init__.py
│       ├── departments.py # Department management
│       ├── users.py       # User management
│       ├── parking.py     # Parking management
│       ├── links.py       # Live chat link management
│       └── system.py      # System info/health
├── pyproject.toml         # Python project config
├── requirements.txt       # Dependencies
├── README.md
└── CLAUDE.md
```

## 3CX Configuration REST API (XAPI)

**Documentation:** https://www.3cx.com/docs/configuration-rest-api-endpoints/

### Authentication
- OAuth2 with client_credentials grant
- Token endpoint: `POST https://{PBX_FQDN}/connect/token`
- Token expires after 60 minutes
- Required parameters:
  - `client_id`: Service Principal client ID (DN of the route point, configured in 3CX)
  - `client_secret`: Service Principal API key (shown only once after creation)
  - `grant_type`: `client_credentials` (fixed)
- Base URL format: `https://{PBX_FQDN}/xapi/v1/`

### OData Query Parameters
- `$filter` - Filter results (e.g., `Name eq 'DEFAULT'`)
- `$top` - Limit results (pagination, default 100)
- `$skip` - Skip records (pagination, default 0)
- `$expand` - Expand related entities (e.g., `Groups(Rights())`)
- `$select` - Specify fields to return
- `$orderby` - Sort order (e.g., `Number`)

### Key API Endpoints (To Be Mapped to MCP Tools)

#### System
- `GET /xapi/v1/Defs?$select=Id` - Get 3CX version (health check)
- `GET /xapi/v1/Groups?$expand=Members` - List departments with members

#### Departments (Groups)
- `GET /xapi/v1/Groups` - List all departments
- `GET /xapi/v1/Groups?$filter=Name eq '{name}'` - Check if department exists
- `POST /xapi/v1/Groups` - Create department
- `PATCH /xapi/v1/Groups({id})` - Update department
- `POST /xapi/v1/Groups/Pbx.DeleteCompanyById` - Delete department

#### Users
- `GET /xapi/v1/Users` - List users (supports pagination)
- `GET /xapi/v1/Users?$filter=tolower(EmailAddress) eq '{email}'` - Check if user exists
- `POST /xapi/v1/Users` - Create user
- `PATCH /xapi/v1/Users({id})` - Update user
- `POST /xapi/v1/Users/Pbx.BatchDelete` - Delete users in batch

#### Parking
- `GET /xapi/v1/Parkings` - List parking slots
- `GET /xapi/v1/Parkings/Pbx.GetByNumber(number='{number}')` - Get parking by number
- `POST /xapi/v1/Parkings` - Create shared parking
- `DELETE /xapi/v1/Parkings({id})` - Delete parking

#### Live Chat Links
- `GET /xapi/v1/WebsiteLinks?$filter=Link eq '{link}'` - Check if URL exists
- `POST /xapi/v1/WebsiteLinks` - Create live chat URL
- `POST /xapi/v1/WebsiteLinks/Pbx.ValidateLink` - Validate friendly URL

## MCP Tools to Implement

### System Tools
1. `get_system_info()` - Get 3CX version info
2. `list_departments()` - Get all configured departments

### Department Management
1. `create_department(params)` - Create new department
2. `update_department(id, params)` - Modify department settings
3. `delete_department(id)` - Remove department
4. `get_department_details(id)` - Get specific department info
5. `get_department_members(id)` - List members in a department

### User Management
1. `list_users()` - Get all users (with pagination)
2. `create_user(params)` - Create new user
3. `update_user(id, params)` - Modify user settings
4. `delete_users(ids)` - Delete users in batch
5. `check_user_exists(email)` - Check if user email exists

### Parking Management
1. `list_parking()` - Get all parking slots
2. `create_parking(params)` - Create shared parking
3. `delete_parking(id)` - Remove parking
4. `get_parking_by_number(number)` - Get parking by number

### Live Chat Management
1. `check_link_exists(link)` - Check if live chat URL exists
2. `create_link(params)` - Create live chat URL
3. `validate_link(friendly_name, pair)` - Validate friendly URL

## Skills

The project includes two quality-focused skills in `.claude/skills/`:

### Humanizer (`humanizer/SKILL.md`)
Removes signs of AI-generated writing from text to make it sound natural and human.

**When to use:**
- Writing or reviewing documentation
- Creating user-facing content
- Improving existing text that feels AI-generated

**Key patterns to avoid:**
- Significance inflation words ("pivotal", "vital role", "testament to")
- AI vocabulary ("additionally", "delve", "showcase", "underscore", "landscape")
- Copula avoidance ("serves as", "features", "boasts" instead of "is"/"has")
- Em dash overuse, emojis, boldface abuse
- Chatbot artifacts ("I hope this helps!", "Let me know if...")

**Invoking:** `/humanizer` followed by text to humanize

### Anti-Slop (`anti-slop/SKILL.md`)
Comprehensive toolkit for detecting and eliminating generic AI patterns in natural language, code, and design.

**When to use:**
- Reviewing content before delivery
- Establishing quality standards
- Cleaning up generic patterns

**For text:**
- Run detection: `python .claude/skills/anti-slop/scripts/detect_slop.py <file>`
- Run cleanup: `python .claude/skills/anti-slop/scripts/clean_slop.py <file> --save`

**For code:**
- Avoid generic variable names (`data`, `result`, `temp`, `item`)
- Remove obvious comments that restate code
- Avoid unnecessary abstraction layers

**For design:**
- Avoid generic gradients (purple/pink/cyan)
- Avoid "Empower your business" style copy
- Design for content, not templates

## Code Quality Standards

### Naming Conventions
- Be specific: `userPreferences` not `data`, `extensionConfig` not `result`
- Functions should describe action + object: `fetchExtensions()` not `getData()`
- Classes should describe responsibility: `ThreeCXClient` not `Manager`

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
- Use straight quotes (`"`) not curly quotes (`"`)
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
- "navigate the complexities" → "handle" or delete

## Configuration

Environment variables required:
- `THREECX_SERVER_URL` - Full URL to 3CX server (e.g., `https://pbx.example.com`)
- `THREECX_CLIENT_ID` - Service Principal client ID (DN of the route point)
- `THREECX_CLIENT_SECRET` - Service Principal API key (shown only once)
- Optional: `THREECX_PORT` - Port number (defaults to 5001 for HTTPS)

### License Requirement
The Configuration API requires an 8SC and higher ENT/AI or ENT+ license.

### Service Principal Setup
To enable API access, you must configure a Service Principal in 3CX:
1. Go to 3CX Web Client > Integrations > API
2. Press "Add" to create a new client application
3. Specify the Client ID (DN for accessing the route point)
4. Check "3CX Configuration API Access" checkbox
5. Specify Department and Role for appropriate access level
6. System Owner/System Admin grants system-wide rights
7. Save the API key (client_secret) - shown only once

### Token Types
- **Multi-Company Admin Tokens:** Full access to manage all departments and entities
- **User Tokens:** Limited access based on assigned roles and departmental permissions

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the MCP client (exposes tools to LLM via stdio)
python -m src.main

# For development with stdio transport
uv run src/main.py
```

## Session Notes

### 2026-03-04
- Project initialized with README.md
- Key resources identified (3CX API docs, MCP Python SDK)
- CLAUDE.md created to capture project context
- Two quality skills incorporated from `.claude/skills/`:
  - **humanizer**: Removes AI writing patterns, based on Wikipedia's "Signs of AI writing"
  - **anti-slop**: Detects/cleans generic AI patterns in text, code, and design
- Code quality and writing standards added to CLAUDE.md
- **Architecture Clarification**: This is an MCP client (using FastMCP) that exposes 3CX API functionality as MCP tools to LLMs
- **API Discovery**: Retrieved official 3CX XAPI endpoint specifications
  - Authentication is OAuth2 client_credentials, not Basic Auth
  - Base URL is `/xapi/v1/`, not `/api/config`
  - Uses OData-style query parameters ($filter, $top, $skip, $expand, $select)
  - Token expires after 60 minutes
  - Available endpoints: Groups, Users, Parkings, WebsiteLinks, Defs
- Next step: Set up Python project structure with correct API details

## Questions for Implementation

1. Does the 3CX API support refresh tokens or only expires_at?
2. What additional endpoints exist beyond Groups, Users, Parkings, and WebsiteLinks?
3. Are there rate limits on the 3CX API?
4. Should we implement async requests for better concurrency?
5. Can we manage call queues/ring groups via the API? (not documented in endpoint specs)