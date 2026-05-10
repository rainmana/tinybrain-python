"""Typer CLI for TinyBrain."""

import asyncio
import os
from datetime import datetime
from pathlib import Path

import typer
from loguru import logger

from tinybrain.config import settings
from tinybrain.database import Database
from tinybrain.log_config import setup_logging

app = typer.Typer(
    name="tinybrain",
    help="Security-focused LLM memory storage MCP server",
    add_completion=False,
)

_default_cog_path = Path(settings.cog_path_prefix) / settings.cog_home


@app.command()
def serve(
    cog_path: Path = typer.Option(
        _default_cog_path,
        "--cog-path",
        "-d",
        help="Path to CogDB data directory",
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

    os.environ["FASTMCP_LOG_LEVEL"] = "CRITICAL"

    logging.basicConfig(level=logging.CRITICAL)
    for logger_name in ["fastmcp", "mcp", "httpx", "httpcore"]:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        logging.getLogger(logger_name).propagate = False

    settings.cog_path_prefix = str(cog_path.parent)
    settings.cog_home = cog_path.name
    settings.log_level = log_level

    setup_logging(mcp_mode=True)

    from tinybrain.mcp import mcp

    mcp.run(show_banner=False)


@app.command()
def init(
    cog_path: Path = typer.Option(
        _default_cog_path,
        "--cog-path",
        "-d",
        help="Path to CogDB data directory",
    ),
) -> None:
    """Initialize the TinyBrain database."""
    setup_logging()

    async def init_db():
        db = Database(cog_path)
        await db.initialize()
        await db.close()
        logger.info(f"CogDB initialized: {cog_path}")

    asyncio.run(init_db())
    typer.echo(f"Database initialized: {cog_path}")


@app.command()
def stats(
    cog_path: Path = typer.Option(
        _default_cog_path,
        "--cog-path",
        "-d",
        help="Path to CogDB data directory",
    ),
) -> None:
    """Show database statistics."""
    setup_logging()

    async def show_stats():
        db = Database(cog_path)
        await db.initialize()

        memories = await db.search_memories(limit=100000)
        session_ids = {m.session_id for m in memories}

        rel_count = 0
        if db._graph:

            def _count():
                result = db._graph.v().has("_type", "relationship").all()
                return len(result.get("result", [])) if result else 0

            rel_count = await asyncio.to_thread(_count)

        await db.close()

        typer.echo("\nTinyBrain Statistics")
        typer.echo(f"  Sessions: {len(session_ids)}")
        typer.echo(f"  Memories: {len(memories)}")
        typer.echo(f"  Relationships: {rel_count}")
        typer.echo()

    asyncio.run(show_stats())


@app.command()
def cleanup(
    cog_path: Path = typer.Option(
        _default_cog_path,
        "--cog-path",
        "-d",
        help="Path to CogDB data directory",
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
        from datetime import timedelta

        db = Database(cog_path)
        await db.initialize()

        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        all_memories = await db.search_memories(limit=100000)
        old_memories = [
            m
            for m in all_memories
            if m.created_at < cutoff
        ]

        if dry_run:
            typer.echo(
                f"Would delete {len(old_memories)} memories older than {max_age_days} days"
            )
        else:
            for m in old_memories:
                await db.delete_memory(m.id)
            typer.echo(
                f"Deleted {len(old_memories)} memories older than {max_age_days} days"
            )

        await db.close()

    asyncio.run(cleanup_old())


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8080, help="Port to bind to"),
    cog_path: Path = typer.Option(
        _default_cog_path,
        "--cog-path",
        "-d",
        help="Path to CogDB data directory",
    ),
) -> None:
    """Start the web interface."""
    import uvicorn

    os.environ["TINYBRAIN_COG_HOME"] = cog_path.name
    os.environ["TINYBRAIN_COG_PATH_PREFIX"] = str(cog_path.parent)

    setup_logging()
    logger.info(f"Starting web interface at http://{host}:{port}")

    from tinybrain.web import app as web_app

    uvicorn.run(web_app, host=host, port=port)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
