"""
FastAPI web application and API for Slidex.
Migrated from Flask to support async operations with LightRAG.
"""

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional, List
import json
import traceback
import tempfile
import shutil
import asyncio
import uuid

from starlette.middleware.sessions import SessionMiddleware

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.ingest import ingest_engine
from slidex.core.search import search_engine
from slidex.core.assembler import slide_assembler
from slidex.core.database import db
from slidex.core.graph_visualizer import graph_visualizer
from slidex.core.deps import get_current_user_optional
from slidex.api.routers.auth import router as auth_router

# Initialize FastAPI app
app = FastAPI(title="Slidex", description="PowerPoint slide management with semantic search")

# Add SessionMiddleware for Authlib state management
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)

# Include Auth Router
app.include_router(auth_router)

# Setup templates
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

# Setup static files
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# ============= Middleware =============

@app.middleware("http")
async def enforce_authentication(request: Request, call_next):
    """
    Middleware to enforce authentication on all routes except:
    - /auth/* (login, callback, logout)
    - /static/* (css, js, images)
    - /health (health check)
    - /favicon.ico
    """
    path = request.url.path
    
    # Define exempt paths
    exempt_prefixes = ["/auth", "/static", "/health"]
    exempt_paths = ["/favicon.ico"]
    
    # Check if path is exempt
    is_exempt = any(path.startswith(prefix) for prefix in exempt_prefixes) or path in exempt_paths
    
    if is_exempt:
        return await call_next(request)
    
    # Check for authenticated user
    user = await get_current_user_optional(request)
    if not user:
        # If not authenticated, redirect or return 401
        if path.startswith("/api"):
            return JSONResponse(
                status_code=401,
                content={"error": "Not authenticated", "detail": "Authentication required"}
            )
        else:
            return RedirectResponse(url="/auth/login")
            
    # Proceed to the actual route
    return await call_next(request)


# ============= Web UI Routes =============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user: Optional[dict] = Depends(get_current_user_optional)):
    """Home page with search interface."""
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.get("/ingest", response_class=HTMLResponse)
async def ingest_page(request: Request, user: Optional[dict] = Depends(get_current_user_optional)):
    """Ingest page."""
    return templates.TemplateResponse("ingest.html", {"request": request, "user": user})


@app.get("/decks", response_class=HTMLResponse)
async def decks_page(request: Request, user: Optional[dict] = Depends(get_current_user_optional)):
    """View all decks."""
    decks = db.get_all_decks()
    return templates.TemplateResponse("decks.html", {"request": request, "decks": decks, "user": user})


@app.get("/graph", response_class=HTMLResponse)
async def graph_page(request: Request, user: Optional[dict] = Depends(get_current_user_optional)):
    """Knowledge graph visualization page."""
    return templates.TemplateResponse("graph.html", {"request": request, "user": user})


# ============= API Routes =============

@app.post("/api/ingest/file")
async def api_ingest_file(request: Request):
    """
    Ingest a single PowerPoint file.
    Body: { "path": "/path/to/file.pptx", "uploader": "optional" }
    """
    try:
        data = await request.json()
        
        if not data or 'path' not in data:
            raise HTTPException(status_code=400, detail="Missing required field: path")
        
        file_path = Path(data['path'])
        uploader = data.get('uploader')
        
        logger.info(f"API: Ingesting file {file_path}")
        
        # Run the sync ingest_file in a thread to avoid blocking the event loop
        deck_id = await asyncio.to_thread(
            ingest_engine.ingest_file, file_path, uploader=uploader
        )
        
        if deck_id:
            return {
                'success': True,
                'deck_id': deck_id,
                'message': 'File ingested successfully'
            }
        else:
            return {
                'success': False,
                'message': 'File already ingested (duplicate)'
            }
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"API error ingesting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest/folder")
async def api_ingest_folder(request: Request):
    """
    Ingest all PowerPoint files in a folder.
    Body: { "path": "/path/to/folder", "recursive": true, "uploader": "optional" }
    """
    try:
        data = await request.json()
        
        if not data or 'path' not in data:
            raise HTTPException(status_code=400, detail="Missing required field: path")
        
        folder_path = Path(data['path'])
        recursive = data.get('recursive', True)
        uploader = data.get('uploader')
        
        logger.info(f"API: Ingesting folder {folder_path} (recursive={recursive})")
        
        # Run the sync ingest_folder in a thread to avoid blocking the event loop
        deck_ids = await asyncio.to_thread(
            ingest_engine.ingest_folder,
            folder_path,
            recursive=recursive,
            uploader=uploader
        )
        
        return {
            'success': True,
            'deck_ids': deck_ids,
            'count': len(deck_ids),
            'message': f'{len(deck_ids)} new decks ingested'
        }
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"API error ingesting folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest/upload")
async def api_ingest_upload(
    files: List[UploadFile] = File(...),
    uploader: Optional[str] = Form(None)
):
    """
    Upload and ingest PowerPoint files via web interface.
    Supports multiple file uploads.
    Files are saved to the configured storage directory.
    """
    results = []
    uploaded_files = []
    
    try:
        # Create uploads directory in storage if it doesn't exist
        uploads_dir = settings.storage_root / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        for upload_file in files:
            try:
                # Validate filename exists
                if not upload_file.filename:
                    results.append({
                        'filename': 'unknown',
                        'success': False,
                        'message': 'No filename provided'
                    })
                    continue
                
                # Validate file extension
                if not upload_file.filename.lower().endswith('.pptx'):
                    results.append({
                        'filename': upload_file.filename,
                        'success': False,
                        'message': 'Only .pptx files are supported'
                    })
                    continue
                
                # Save uploaded file to storage directory
                # Use a unique name to avoid conflicts
                unique_filename = f"{uuid.uuid4().hex}_{upload_file.filename}"
                file_path = uploads_dir / unique_filename
                
                with open(file_path, 'wb') as buffer:
                    shutil.copyfileobj(upload_file.file, buffer)
                
                uploaded_files.append(file_path)
                logger.info(f"Saved uploaded file: {file_path}")
                
                # Ingest the file
                deck_id = await asyncio.to_thread(
                    ingest_engine.ingest_file,
                    file_path,
                    uploader=uploader
                )
                
                if deck_id:
                    results.append({
                        'filename': upload_file.filename,
                        'success': True,
                        'deck_id': deck_id,
                        'message': 'File ingested successfully'
                    })
                else:
                    results.append({
                        'filename': upload_file.filename,
                        'success': False,
                        'message': 'File already ingested (duplicate)'
                    })
                    
            except Exception as e:
                logger.error(f"Error processing {upload_file.filename}: {e}")
                logger.error(traceback.format_exc())
                results.append({
                    'filename': upload_file.filename,
                    'success': False,
                    'message': str(e)
                })
        
        # Count successes
        success_count = sum(1 for r in results if r['success'])
        
        return {
            'success': success_count > 0,
            'results': results,
            'total': len(files),
            'ingested': success_count,
            'message': f'{success_count} of {len(files)} files ingested successfully'
        }
        
    except Exception as e:
        logger.error(f"API error in upload: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search")
async def api_search(request: Request):
    """Search for slides.

    Body: {
        "query": "search text",
        "top_k": 10 (optional, defaults to settings.top_k_results),
        "mode": "hybrid"  # naive, local, global, or hybrid (LightRAG modes)
    }

    When LightRAG is enabled, the response also includes a natural language
    answer in `lightrag_response` summarizing the query.
    """
    try:
        data = await request.json()
        
        if not data or 'query' not in data:
            raise HTTPException(status_code=400, detail="Missing required field: query")
        
        query = data['query']
        # Use top_k from request if provided, otherwise use default from settings
        top_k = data.get('top_k', settings.top_k_results)
        mode = data.get('mode', 'hybrid')
        
        # Validate mode
        valid_modes = ['naive', 'local', 'global', 'hybrid']
        if mode not in valid_modes:
            raise HTTPException(
                status_code=400,
                detail=f'Invalid mode. Must be one of: {valid_modes}'
            )
        
        logger.info(f"API: Searching for '{query}' (top_k={top_k}, mode={mode})")
        
        try:
            search_result = await search_engine.search(query, top_k=top_k, mode=mode)
            results = search_result.get('results', [])
            lightrag_response = search_result.get('response')
        except Exception as e:
            logger.error(f"Error in API search: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=str(e))

        return {
            'success': True,
            'results': results,
            'count': len(results),
            'mode': mode,
            'response': lightrag_response,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API error searching: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/slide/{slide_id}/preview")
async def api_slide_preview(slide_id: str):
    """Get slide preview metadata."""
    try:
        slide = db.get_slide_by_id(slide_id)
        
        if not slide:
            raise HTTPException(status_code=404, detail="Slide not found")
        
        return {
            'success': True,
            'slide': slide
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API error getting slide preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assemble")
async def api_assemble(request: Request):
    """Assemble slides into a new presentation.

    The API now always produces **both** PPTX and PDF outputs for simplicity.
    Body: {
        "slide_ids": ["id1", "id2"],
        "output_filename": "optional.pptx",
        "preserve_order": true
    }
    """
    try:
        data = await request.json()
        
        if not data or 'slide_ids' not in data:
            raise HTTPException(status_code=400, detail="Missing required field: slide_ids")
        
        slide_ids = data['slide_ids']
        output_filename = data.get('output_filename')
        preserve_order = data.get('preserve_order', True)
        
        if not isinstance(slide_ids, list) or not slide_ids:
            raise HTTPException(status_code=400, detail="slide_ids must be a non-empty list")

        logger.info(f"API: Assembling {len(slide_ids)} slides into PPTX and PDF")

        # First assemble PPTX
        pptx_path = slide_assembler.assemble(
            slide_ids,
            output_filename=output_filename,
            preserve_order=preserve_order,
        )

        # Then assemble PDF using per-slide PDFs
        from slidex.core.pdf_assembler import pdf_assembler
        pdf_path = pdf_assembler.assemble(
            slide_ids,
            preserve_order=preserve_order,
        )
        
        return {
            'success': True,
            'pptx_file': str(pptx_path),
            'pptx_download_url': f'/api/download/{pptx_path.name}',
            'pdf_file': str(pdf_path),
            'pdf_download_url': f'/api/download/{pdf_path.name}',
            'slide_count': len(slide_ids),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API error assembling slides: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{filename}")
async def api_download(filename: str):
    """Download an assembled presentation."""
    try:
        # exports_dir is relative to project root
        file_path = settings.exports_dir
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        file_path = file_path / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Infer content type
        if filename.lower().endswith('.pdf'):
            media_type = 'application/pdf'
        else:
            media_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        
        return FileResponse(
            file_path,
            media_type=media_type,
            filename=filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API error downloading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/thumbnails/{filepath:path}")
async def api_thumbnail(filepath: str):
    """Serve thumbnail images."""
    try:
        # Filepath from database is already relative to project root
        thumbnail_path = Path(filepath)
        
        # If it's not absolute, make it relative to project root
        if not thumbnail_path.is_absolute():
            thumbnail_path = Path.cwd() / thumbnail_path
        
        if not thumbnail_path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        
        return FileResponse(thumbnail_path, media_type='image/png')
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API error serving thumbnail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/decks")
async def api_get_decks():
    """Get all decks."""
    try:
        decks = db.get_all_decks()
        return {
            'success': True,
            'decks': decks,
            'count': len(decks)
        }
    except Exception as e:
        logger.error(f"API error getting decks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/data")
async def api_graph_data():
    """Get knowledge graph data for visualization."""
    try:
        if not settings.lightrag_enabled:
            raise HTTPException(status_code=400, detail="LightRAG is not enabled")
        
        graph_data = graph_visualizer.export_graph_data()
        return {
            'success': True,
            'graph': graph_data
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API error getting graph data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/stats")
async def api_graph_stats():
    """Get knowledge graph statistics."""
    try:
        if not settings.lightrag_enabled:
            raise HTTPException(status_code=400, detail="LightRAG is not enabled")
        
        stats = graph_visualizer.get_graph_stats()
        return {
            'success': True,
            'stats': stats
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API error getting graph stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {'status': 'healthy', 'service': 'slidex'}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port
    )

