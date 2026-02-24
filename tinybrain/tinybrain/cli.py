"""CLI interface for TinyBrain."""

import asyncio
import os
import sys
from pathlib import Path

import click

from tinybrain.mcp.server import create_mcp_server


@click.group()
@click.version_option(version="2.0.0")
def cli():
    """TinyBrain - Security-focused LLM memory storage system."""
    pass


@cli.command()
@click.option(
    "--db-path",
    type=click.Path(),
    default=str(Path.home() / ".tinybrain" / "data.db"),
    help="Path to the SQLite database file",
)
@click.option(
    "--chromadb",
    is_flag=True,
    help="Use ChromaDB for semantic search (requires chromadb package)",
)
def serve(db_path: str, chromadb: bool):
    """Start the TinyBrain MCP server."""
    click.echo("🧠 Starting TinyBrain MCP Server...")
    click.echo(f"Database: {db_path}")
    
    if chromadb:
        click.echo("Using ChromaDB for semantic search")
    
    try:
        # Create and run the MCP server
        mcp = create_mcp_server(db_path=db_path, use_chromadb=chromadb)
        
        # FastMCP runs via stdio by default
        click.echo("MCP server ready (stdio transport)")
        click.echo("Waiting for MCP requests...")
        
        # Run the server
        mcp.run()
        
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--db-path",
    type=click.Path(),
    default=str(Path.home() / ".tinybrain" / "data.db"),
    help="Path to the SQLite database file",
)
def ui(db_path: str):
    """Launch the Streamlit UI."""
    import subprocess
    
    ui_path = Path(__file__).parent / "ui" / "app.py"
    
    if not ui_path.exists():
        click.echo(f"Error: UI file not found at {ui_path}", err=True)
        sys.exit(1)
    
    click.echo("🎨 Launching TinyBrain UI...")
    click.echo(f"Database: {db_path}")
    
    # Set environment variable for database path
    env = dict(os.environ)
    env["TINYBRAIN_DB_PATH"] = db_path
    
    # Run streamlit
    subprocess.run(
        ["streamlit", "run", str(ui_path)],
        env=env,
    )


@cli.command()
@click.option(
    "--db-path",
    type=click.Path(),
    default=str(Path.home() / ".tinybrain" / "data.db"),
    help="Path to the SQLite database file",
)
def stats(db_path: str):
    """Show database statistics."""
    import asyncio
    from tinybrain.database import Database, SQLiteBackend
    
    async def show_stats():
        backend = SQLiteBackend(db_path)
        db = Database(backend)
        await db.initialize()
        
        try:
            stats = await db.get_stats()
            click.echo("📊 Database Statistics:")
            click.echo(f"  Sessions: {stats.get('sessions_count', 0)}")
            click.echo(f"  Memory Entries: {stats.get('memory_entries_count', 0)}")
            click.echo(f"  Relationships: {stats.get('relationships_count', 0)}")
            click.echo(f"  Context Snapshots: {stats.get('context_snapshots_count', 0)}")
            click.echo(f"  Task Progress Entries: {stats.get('task_progress_count', 0)}")
            click.echo(f"  Database Size: {stats.get('database_size_bytes', 0) / 1024 / 1024:.2f} MB")
            
            top_accessed = stats.get("top_accessed_entries", [])
            if top_accessed:
                click.echo("\n🔝 Top Accessed Entries:")
                for entry in top_accessed:
                    click.echo(f"  - {entry['title']} (accessed {entry['access_count']} times)")
        finally:
            await db.close()
    
    asyncio.run(show_stats())


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()

