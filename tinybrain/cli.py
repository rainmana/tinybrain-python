"""Typer CLI for TinyBrain."""

import asyncio
from datetime import datetime
from pathlib import Path

import typer
from loguru import logger

from tinybrain.config import settings
from tinybrain.database import Database
from tinybrain.logging import setup_logging

app = typer.Typer(
    name="tinybrain",
    help="Security-focused LLM memory storage MCP server",
    add_completion=False,
)


@app.command()
def serve(
    db_path: Path = typer.Option(
        settings.db_path,
        "--db-path",
        "-d",
        help="Path to SQLite database",
    ),
    log_level: str = typer.Option(
        settings.log_level,
        "--log-level",
        "-l",
        help="Log level (DEBUG, INFO, WARNING, ERROR)",
    ),
) -> None:
    """Start the TinyBrain MCP server."""
    import logging
    import os
    
    # Disable all console output for MCP mode
    os.environ["FASTMCP_LOG_LEVEL"] = "CRITICAL"
    
    # Suppress all logging to console
    logging.basicConfig(level=logging.CRITICAL)
    for logger_name in ["fastmcp", "mcp", "httpx", "httpcore"]:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        logging.getLogger(logger_name).propagate = False
    
    # Update settings
    settings.db_path = db_path
    settings.log_level = log_level

    # Setup logging in MCP mode (no console output)
    setup_logging(mcp_mode=True)

    # Import and run the MCP server without banner
    from tinybrain.mcp import mcp
    mcp.run(show_banner=False)


@app.command()
def init(
    db_path: Path = typer.Option(
        settings.db_path,
        "--db-path",
        "-d",
        help="Path to SQLite database",
    ),
) -> None:
    """Initialize the TinyBrain database."""
    setup_logging()

    async def init_db():
        db = Database(db_path)
        await db.initialize()
        await db.close()
        logger.info(f"Database initialized: {db_path}")

    asyncio.run(init_db())
    typer.echo(f"✓ Database initialized: {db_path}")


@app.command()
def stats(
    db_path: Path = typer.Option(
        settings.db_path,
        "--db-path",
        "-d",
        help="Path to SQLite database",
    ),
) -> None:
    """Show database statistics."""
    setup_logging()

    async def show_stats():
        db = Database(db_path)
        await db.connect()

        # Get counts
        cursor = await db._conn.execute("SELECT COUNT(*) FROM sessions")
        sessions = (await cursor.fetchone())[0]

        cursor = await db._conn.execute("SELECT COUNT(*) FROM memory_entries")
        memories = (await cursor.fetchone())[0]

        cursor = await db._conn.execute("SELECT COUNT(*) FROM relationships")
        relationships = (await cursor.fetchone())[0]

        await db.close()

        typer.echo("\n📊 TinyBrain Statistics")
        typer.echo(f"  Sessions: {sessions}")
        typer.echo(f"  Memories: {memories}")
        typer.echo(f"  Relationships: {relationships}")
        typer.echo()

    asyncio.run(show_stats())


@app.command()
def cleanup(
    db_path: Path = typer.Option(
        settings.db_path,
        "--db-path",
        "-d",
        help="Path to SQLite database",
    ),
    max_age_days: int = typer.Option(
        30,
        "--max-age",
        "-a",
        help="Maximum age in days",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview without deleting",
    ),
) -> None:
    """Clean up old memories."""
    setup_logging()

    async def cleanup_old():
        db = Database(db_path)
        await db.connect()

        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        cursor = await db._conn.execute(
            "SELECT COUNT(*) FROM memory_entries WHERE created_at < ?",
            (cutoff.isoformat(),),
        )
        count = (await cursor.fetchone())[0]

        if dry_run:
            typer.echo(f"Would delete {count} memories older than {max_age_days} days")
        else:
            await db._conn.execute(
                "DELETE FROM memory_entries WHERE created_at < ?",
                (cutoff.isoformat(),),
            )
            await db._conn.commit()
            typer.echo(f"✓ Deleted {count} memories older than {max_age_days} days")

        await db.close()

    asyncio.run(cleanup_old())


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8080, help="Port to bind to"),
    db_path: Path = typer.Option(
        settings.db_path,
        "--db-path",
        "-d",
        help="Path to SQLite database",
    ),
) -> None:
    """Start the web interface."""
    import uvicorn
    import os
    
    # Set database path
    os.environ["TINYBRAIN_DB_PATH"] = str(db_path)
    
    setup_logging()
    logger.info(f"Starting web interface at http://{host}:{port}")
    
    from tinybrain.web import app as web_app
    uvicorn.run(web_app, host=host, port=port)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
