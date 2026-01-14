"""
CLI interface for Slidex using Typer.
"""

import typer
from pathlib import Path
from typing import Optional, List
import json
import sys

from slidex.logging_config import logger
from slidex.core.ingest import ingest_engine
from slidex.core.search import search_engine
from slidex.core.assembler import slide_assembler


app = typer.Typer(
    name="slidex",
    help="Slidex - PowerPoint slide management with semantic search",
    add_completion=False,
)

ingest_app = typer.Typer(help="Ingest PowerPoint files")
app.add_typer(ingest_app, name="ingest")


@ingest_app.command("file")
def ingest_file(
    path: str = typer.Argument(..., help="Path to the .pptx file"),
    uploader: Optional[str] = typer.Option(None, help="Uploader name"),
):
    """Ingest a single PowerPoint file."""
    try:
        file_path = Path(path)
        typer.echo(f"Ingesting file: {file_path}")
        
        deck_id = ingest_engine.ingest_file(file_path, uploader=uploader)
        
        if deck_id:
            typer.secho(
                f"✓ File ingested successfully. Deck ID: {deck_id}",
                fg=typer.colors.GREEN
            )
        else:
            typer.secho(
                "File already ingested (duplicate), skipping.",
                fg=typer.colors.YELLOW
            )
    
    except Exception as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@ingest_app.command("folder")
def ingest_folder(
    path: str = typer.Argument(..., help="Path to the folder"),
    recursive: bool = typer.Option(True, help="Search recursively"),
    uploader: Optional[str] = typer.Option(None, help="Uploader name"),
):
    """Ingest all PowerPoint files in a folder."""
    try:
        folder_path = Path(path)
        typer.echo(f"Ingesting folder: {folder_path} (recursive={recursive})")
        
        deck_ids = ingest_engine.ingest_folder(
            folder_path,
            recursive=recursive,
            uploader=uploader
        )
        
        typer.secho(
            f"✓ Folder ingestion complete. {len(deck_ids)} new decks ingested.",
            fg=typer.colors.GREEN
        )
    
    except Exception as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(10, help="Number of results to return"),
    mode: str = typer.Option("hybrid", help="Query mode: naive, local, global, or hybrid (LightRAG)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Search for slides using semantic search with LightRAG."""
    try:
        # Validate mode
        valid_modes = ['naive', 'local', 'global', 'hybrid']
        if mode not in valid_modes:
            typer.secho(
                f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}",
                fg=typer.colors.RED, err=True
            )
            raise typer.Exit(code=1)
        
        typer.echo(f"Searching for: '{query}' (mode={mode})")
        
        results = search_engine.search(query, top_k=top_k, mode=mode)
        
        if not results:
            typer.secho("No results found.", fg=typer.colors.YELLOW)
            return
        
        if json_output:
            # Output as JSON
            print(json.dumps(results, indent=2, default=str))
        else:
            # Human-readable output
            typer.secho(f"\nFound {len(results)} results:\n", fg=typer.colors.GREEN)
            
            for i, result in enumerate(results, 1):
                typer.echo(f"{i}. {result['title_header'] or '[No title]'}")
                typer.echo(f"   Deck: {result['deck_filename']} (Slide {result['slide_index'] + 1})")
                typer.echo(f"   Summary: {result['summary']}")
                typer.echo(f"   Score: {result['score']:.4f}")
                typer.echo(f"   Slide ID: {result['slide_id']}")
                typer.echo()
    
    except Exception as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command("assemble")
def assemble(
    slide_ids: str = typer.Option(..., "--slide-ids", help="Comma-separated list of slide IDs"),
    output: Optional[str] = typer.Option(None, "--output", help="Output filename"),
    preserve_order: bool = typer.Option(False, "--preserve-order", help="Preserve slide order"),
):
    """Assemble selected slides into a new presentation."""
    try:
        # Parse slide IDs
        slide_id_list = [s.strip() for s in slide_ids.split(",")]
        
        typer.echo(f"Assembling {len(slide_id_list)} slides...")
        
        output_path = slide_assembler.assemble(
            slide_id_list,
            output_filename=output,
            preserve_order=preserve_order
        )
        
        typer.secho(
            f"✓ Presentation assembled successfully: {output_path}",
            fg=typer.colors.GREEN
        )
    
    except Exception as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command("version")
def version():
    """Show version information."""
    from slidex import __version__
    typer.echo(f"Slidex version {__version__}")


if __name__ == "__main__":
    app()
