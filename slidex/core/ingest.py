"""
Ingestion engine for processing PowerPoint files.
Handles file discovery, deduplication, text extraction, embedding generation, and storage.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional, List
from pptx import Presentation

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.database import db
from slidex.core.ollama_client import ollama_client
from slidex.core.slide_processor import slide_processor
from slidex.core.vector_index import vector_index


class IngestEngine:
    """Engine for ingesting PowerPoint presentations."""
    
    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        # Include file size and mtime for extra uniqueness
        stat = file_path.stat()
        hash_input = f"{sha256_hash.hexdigest()}_{stat.st_size}_{stat.st_mtime}"
        
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    @staticmethod
    def ingest_file(
        file_path: Path,
        uploader: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Ingest a single PowerPoint file.
        
        Args:
            file_path: Path to the .pptx file
            uploader: Optional uploader name
            session_id: Optional session ID for audit logging
            
        Returns:
            deck_id if successful, None if skipped (duplicate)
        """
        file_path = Path(file_path).resolve()
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.suffix.lower() == '.pptx':
            logger.error(f"Not a PowerPoint file: {file_path}")
            raise ValueError(f"Not a PowerPoint file: {file_path}")
        
        logger.info(f"Starting ingestion: {file_path}")
        
        # Compute file hash
        file_hash = IngestEngine.compute_file_hash(file_path)
        logger.debug(f"File hash: {file_hash}")
        
        # Check if already ingested
        existing_deck_id = db.check_deck_exists(file_hash)
        if existing_deck_id:
            logger.info(f"File already ingested (deck_id: {existing_deck_id}), skipping")
            return None
        
        # Load presentation
        try:
            presentation = Presentation(str(file_path))
        except Exception as e:
            logger.error(f"Error loading presentation: {e}")
            raise
        
        slide_count = len(presentation.slides)
        logger.info(f"Loaded presentation: {slide_count} slides")
        
        # Insert deck record
        deck_id = db.insert_deck(
            file_hash=file_hash,
            original_path=str(file_path),
            filename=file_path.name,
            slide_count=slide_count,
            uploader=uploader,
        )
        
        # Process each slide
        for slide_idx, slide in enumerate(presentation.slides):
            logger.debug(f"Processing slide {slide_idx + 1}/{slide_count}")
            
            # Extract text
            title_header, plain_text = slide_processor.extract_text_from_slide(slide)
            
            if not plain_text.strip():
                logger.warning(f"Slide {slide_idx} has no text, using placeholder")
                plain_text = f"[Slide {slide_idx + 1}]"
            
            # Generate thumbnail
            thumbnail_filename = f"{deck_id}_{slide_idx}.png"
            thumbnail_path = settings.thumbnails_dir / deck_id / thumbnail_filename
            slide_processor.generate_thumbnail(
                presentation,
                slide_idx,
                thumbnail_path,
                width=settings.thumbnail_width
            )
            
            # Generate summary
            try:
                summary = ollama_client.generate_summary(
                    plain_text,
                    max_words=20,
                    session_id=session_id
                )
            except Exception as e:
                logger.error(f"Error generating summary for slide {slide_idx}: {e}")
                summary = plain_text[:100]  # Fallback to truncated text
            
            # Prepare embedding input
            embedding_input = f"{title_header or ''}\n{plain_text}\n{summary}"
            
            # Generate embedding
            try:
                embedding = ollama_client.generate_embedding(
                    embedding_input[:2000],  # Truncate to avoid token limits
                    session_id=session_id
                )
            except Exception as e:
                logger.error(f"Error generating embedding for slide {slide_idx}: {e}")
                # Skip this slide if embedding fails
                continue
            
            # Add to FAISS index
            vector_id = vector_index.add_vector(embedding)
            
            # Insert slide record
            # Store thumbnail path relative to project root, or absolute if outside
            try:
                # Try to make it relative to current working directory
                rel_thumbnail_path = thumbnail_path.resolve().relative_to(Path.cwd().resolve())
                thumbnail_path_str = str(rel_thumbnail_path)
            except ValueError:
                # If not in subpath, use absolute path
                thumbnail_path_str = str(thumbnail_path.resolve())
            
            slide_id = db.insert_slide(
                deck_id=deck_id,
                slide_index=slide_idx,
                title_header=title_header,
                plain_text=plain_text,
                summary=summary,
                thumbnail_path=thumbnail_path_str,
                original_slide_position=slide_idx,
            )
            
            # Insert FAISS mapping
            db.insert_faiss_mapping(slide_id, vector_id)
            
            logger.debug(f"Slide {slide_idx + 1} processed successfully")
        
        # Save FAISS index
        vector_index.save()
        
        logger.info(f"Ingestion complete: {file_path} (deck_id: {deck_id})")
        return deck_id
    
    @staticmethod
    def ingest_folder(
        folder_path: Path,
        recursive: bool = True,
        uploader: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[str]:
        """
        Ingest all PowerPoint files in a folder.
        
        Args:
            folder_path: Path to the folder
            recursive: Whether to search recursively
            uploader: Optional uploader name
            session_id: Optional session ID for audit logging
            
        Returns:
            List of deck_ids for successfully ingested files
        """
        folder_path = Path(folder_path).resolve()
        
        if not folder_path.exists():
            logger.error(f"Folder not found: {folder_path}")
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        if not folder_path.is_dir():
            logger.error(f"Not a directory: {folder_path}")
            raise ValueError(f"Not a directory: {folder_path}")
        
        logger.info(f"Searching for .pptx files in: {folder_path} (recursive={recursive})")
        
        # Find all .pptx files
        if recursive:
            pptx_files = list(folder_path.rglob("*.pptx"))
        else:
            pptx_files = list(folder_path.glob("*.pptx"))
        
        # Filter out temporary files (starting with ~$)
        pptx_files = [f for f in pptx_files if not f.name.startswith("~$")]
        
        logger.info(f"Found {len(pptx_files)} .pptx files")
        
        deck_ids = []
        for pptx_file in pptx_files:
            try:
                deck_id = IngestEngine.ingest_file(pptx_file, uploader, session_id)
                if deck_id:
                    deck_ids.append(deck_id)
            except Exception as e:
                logger.error(f"Error ingesting {pptx_file}: {e}")
                # Continue with other files
                continue
        
        logger.info(f"Folder ingestion complete: {len(deck_ids)} new decks ingested")
        return deck_ids


# Global ingest engine instance
ingest_engine = IngestEngine()
