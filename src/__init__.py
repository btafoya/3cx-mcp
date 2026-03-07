"""
3CX Debugging MCP Server - Main Entry Point.

Runs directly on the 3CX server, providing call flow debugging capabilities
without requiring enterprise XAPI licensing.
"""
import asyncio
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import Config
from .database.connection import DatabasePool, DatabaseError
from .logs.parser import LogParser
from .tools import calls, participants, queues, logs, audit


def create_mcp_server(config: Config) -> tuple[FastMCP, DatabasePool]:
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
    calls.register(mcp, db)
    participants.register(mcp, db)
    queues.register(mcp, db)
    logs.register(mcp, log_parser)
    audit.register(mcp, db)

    # Add health check tool
    @mcp.tool()
    async def health_check() -> dict:
        """Check server health and connectivity."""
        try:
            await db.fetchval("SELECT 1")
            db_status = "connected"
        except DatabaseError as e:
            db_status = f"error: {e}"

        log_status = "accessible" if Path(config.logs.main_log_path).exists() else "missing"

        return {
            "status": "healthy" if db_status == "connected" else "degraded",
            "database": db_status,
            "logs": log_status,
            "config": {
                "database": config.database.database,
                "log_path": config.logs.main_log_path,
                "mcp_name": config.server.mcp_name,
            }
        }

    # Add database info tool
    @mcp.tool()
    async def get_database_info() -> dict:
        """Get database version and available tables."""
        version = await db.fetchval("SELECT version()")
        tables = await db.fetch(
            """SELECT table_name
               FROM information_schema.tables
               WHERE table_schema = 'public'
               ORDER BY table_name"""
        )

        return {
            "version": version,
            "tables": [t["table_name"] for t in tables],
        }

    # Add server info tool
    @mcp.tool()
    async def server_info() -> dict:
        """Get server information and configuration."""
        return {
            "name": config.server.mcp_name,
            "write_operations_enabled": config.server.enable_write_operations,
            "log_path": config.logs.main_log_path,
            "database": {
                "name": config.database.database,
                "user": config.database.user,
                "use_socket": config.database.use_socket,
            },
        }

    return mcp, db


async def main():
    """Main entry point."""
    # Load configuration
    config = Config.from_env()

    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Create server
    mcp, db = create_mcp_server(config)

    # Initialize database pool
    try:
        await db.initialize()
    except ConnectionError as e:
        print(f"Database connection error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        # Run MCP server (stdio transport)
        await mcp.run()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())