# 3CX MCP Client

Model Context Protocol client for 3CX VoIP server. Enables Claude Code and other LLMs to interact with 3CX through its Configuration REST API (XAPI).

## Overview

This MCP client exposes 3CX API functionality as MCP tools, allowing LLMs to:
- Manage departments (Groups)
- Create, update, delete users
- Configure shared parking
- Manage live chat links
- Query system information

## Requirements

- 3CX Version 20+
- 8SC and higher ENT/AI or ENT+ license
- Python 3.10+

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set environment variables:

```bash
export THREECX_SERVER_URL=https://pbx.example.com
export THREECX_CLIENT_ID=your-client-id
export THREECX_CLIENT_SECRET=your-api-key
```

### Service Principal Setup

1. Go to 3CX Web Client > Integrations > API
2. Press "Add" to create a new client application
3. Specify the Client ID (DN for accessing the route point)
4. Check "3CX Configuration API Access" checkbox
5. Specify Department and Role for appropriate access level
6. Save the API key (client_secret) - shown only once

## Usage

Run the MCP client:

```bash
python -m src.main
```

Or with uv:

```bash
uv run src/main.py
```

## Documentation

- [3CX API Reference](./3cx-API.md)
- [Project Documentation](./CLAUDE.md)

## Resources

- [3CX Configuration API Documentation](https://www.3cx.com/docs/configuration-rest-api/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)