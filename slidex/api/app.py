"""
Flask web application and API for Slidex.
"""

from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from pathlib import Path
from typing import Optional
import json

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.ingest import ingest_engine
from slidex.core.search import search_engine
from slidex.core.assembler import slide_assembler
from slidex.core.database import db


app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

app.config['SECRET_KEY'] = 'dev-secret-key'  # Change in production
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size


# ============= Web UI Routes =============

@app.route('/')
def index():
    """Home page with search interface."""
    return render_template('index.html')


@app.route('/ingest')
def ingest_page():
    """Ingest page."""
    return render_template('ingest.html')


@app.route('/decks')
def decks_page():
    """View all decks."""
    decks = db.get_all_decks()
    return render_template('decks.html', decks=decks)


# ============= API Routes =============

@app.route('/api/ingest/file', methods=['POST'])
def api_ingest_file():
    """
    Ingest a single PowerPoint file.
    Body: { "path": "/path/to/file.pptx", "uploader": "optional" }
    """
    try:
        data = request.get_json()
        
        if not data or 'path' not in data:
            return jsonify({'error': 'Missing required field: path'}), 400
        
        file_path = Path(data['path'])
        uploader = data.get('uploader')
        
        logger.info(f"API: Ingesting file {file_path}")
        
        deck_id = ingest_engine.ingest_file(file_path, uploader=uploader)
        
        if deck_id:
            return jsonify({
                'success': True,
                'deck_id': deck_id,
                'message': 'File ingested successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'File already ingested (duplicate)'
            })
    
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"API error ingesting file: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ingest/folder', methods=['POST'])
def api_ingest_folder():
    """
    Ingest all PowerPoint files in a folder.
    Body: { "path": "/path/to/folder", "recursive": true, "uploader": "optional" }
    """
    try:
        data = request.get_json()
        
        if not data or 'path' not in data:
            return jsonify({'error': 'Missing required field: path'}), 400
        
        folder_path = Path(data['path'])
        recursive = data.get('recursive', True)
        uploader = data.get('uploader')
        
        logger.info(f"API: Ingesting folder {folder_path} (recursive={recursive})")
        
        deck_ids = ingest_engine.ingest_folder(
            folder_path,
            recursive=recursive,
            uploader=uploader
        )
        
        return jsonify({
            'success': True,
            'deck_ids': deck_ids,
            'count': len(deck_ids),
            'message': f'{len(deck_ids)} new decks ingested'
        })
    
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"API error ingesting folder: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/search', methods=['POST'])
def api_search():
    """
    Search for slides.
    Body: { "query": "search text", "top_k": 10 }
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing required field: query'}), 400
        
        query = data['query']
        top_k = data.get('top_k', settings.top_k_results)
        
        logger.info(f"API: Searching for '{query}' (top_k={top_k})")
        
        results = search_engine.search(query, top_k=top_k)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    
    except Exception as e:
        logger.error(f"API error searching: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/slide/<slide_id>/preview', methods=['GET'])
def api_slide_preview(slide_id: str):
    """Get slide preview metadata."""
    try:
        slide = db.get_slide_by_id(slide_id)
        
        if not slide:
            return jsonify({'error': 'Slide not found'}), 404
        
        return jsonify({
            'success': True,
            'slide': slide
        })
    
    except Exception as e:
        logger.error(f"API error getting slide preview: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/assemble', methods=['POST'])
def api_assemble():
    """
    Assemble slides into a new presentation.
    Body: { "slide_ids": ["id1", "id2"], "output_filename": "optional.pptx" }
    """
    try:
        data = request.get_json()
        
        if not data or 'slide_ids' not in data:
            return jsonify({'error': 'Missing required field: slide_ids'}), 400
        
        slide_ids = data['slide_ids']
        output_filename = data.get('output_filename')
        preserve_order = data.get('preserve_order', True)
        
        if not isinstance(slide_ids, list) or not slide_ids:
            return jsonify({'error': 'slide_ids must be a non-empty list'}), 400
        
        logger.info(f"API: Assembling {len(slide_ids)} slides")
        
        output_path = slide_assembler.assemble(
            slide_ids,
            output_filename=output_filename,
            preserve_order=preserve_order
        )
        
        # Generate download URL
        download_url = f'/api/download/{output_path.name}'
        
        return jsonify({
            'success': True,
            'output_file': str(output_path),
            'download_url': download_url,
            'slide_count': len(slide_ids)
        })
    
    except Exception as e:
        logger.error(f"API error assembling slides: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<filename>', methods=['GET'])
def api_download(filename: str):
    """Download an assembled presentation."""
    try:
        # exports_dir is relative to project root, not to app.py location
        file_path = settings.exports_dir
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
        file_path = file_path / filename
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        logger.error(f"API error downloading file: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/thumbnails/<path:filepath>', methods=['GET'])
def api_thumbnail(filepath: str):
    """Serve thumbnail images."""
    try:
        # Filepath from database is already relative to project root (storage/thumbnails/...)
        # So we need to resolve it from the project root, not from thumbnails_dir
        thumbnail_path = Path(filepath)
        
        # If it's not absolute, make it relative to project root
        if not thumbnail_path.is_absolute():
            thumbnail_path = Path.cwd() / thumbnail_path
        
        if not thumbnail_path.exists():
            return jsonify({'error': 'Thumbnail not found'}), 404
        
        return send_file(thumbnail_path, mimetype='image/png')
    
    except Exception as e:
        logger.error(f"API error serving thumbnail: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/decks', methods=['GET'])
def api_get_decks():
    """Get all decks."""
    try:
        decks = db.get_all_decks()
        return jsonify({
            'success': True,
            'decks': decks,
            'count': len(decks)
        })
    except Exception as e:
        logger.error(f"API error getting decks: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'slidex'})


if __name__ == '__main__':
    app.run(
        host=settings.flask_host,
        port=settings.flask_port,
        debug=settings.flask_debug
    )
