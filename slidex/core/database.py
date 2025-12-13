"""
Database helper functions for PostgreSQL operations.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime
from contextlib import contextmanager

from slidex.config import settings
from slidex.logging_config import logger


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = psycopg2.connect(settings.database_url)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


class Database:
    """Database operations for Slidex."""
    
    @staticmethod
    def check_deck_exists(file_hash: str) -> Optional[str]:
        """
        Check if a deck with the given file hash already exists.
        
        Args:
            file_hash: SHA256 hash of the file
            
        Returns:
            deck_id if exists, None otherwise
        """
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT deck_id FROM decks WHERE file_hash = %s",
                (file_hash,)
            )
            result = cur.fetchone()
            return str(result['deck_id']) if result else None
    
    @staticmethod
    def insert_deck(
        file_hash: str,
        original_path: str,
        filename: str,
        slide_count: int,
        uploader: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Insert a new deck into the database.
        
        Returns:
            deck_id (UUID as string)
        """
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            deck_id = str(uuid.uuid4())
            
            cur.execute(
                """
                INSERT INTO decks 
                (deck_id, file_hash, original_path, filename, uploader, slide_count, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING deck_id
                """,
                (deck_id, file_hash, original_path, filename, uploader, slide_count, 
                 psycopg2.extras.Json(notes) if notes else None)
            )
            
            result = cur.fetchone()
            logger.info(f"Deck inserted: {deck_id} ({filename})")
            return str(result['deck_id'])
    
    @staticmethod
    def insert_slide(
        deck_id: str,
        slide_index: int,
        title_header: Optional[str],
        plain_text: str,
        summary: str,
        thumbnail_path: str,
        original_slide_position: int,
    ) -> str:
        """
        Insert a new slide into the database.
        
        Returns:
            slide_id (UUID as string)
        """
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            slide_id = str(uuid.uuid4())
            
            cur.execute(
                """
                INSERT INTO slides 
                (slide_id, deck_id, slide_index, title_header, plain_text, 
                 summary_10_20_words, thumbnail_path, original_slide_position)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING slide_id
                """,
                (slide_id, deck_id, slide_index, title_header, plain_text,
                 summary, thumbnail_path, original_slide_position)
            )
            
            result = cur.fetchone()
            logger.debug(f"Slide inserted: {slide_id} (deck: {deck_id}, index: {slide_index})")
            return str(result['slide_id'])
    
    @staticmethod
    def insert_faiss_mapping(slide_id: str, vector_id: int) -> None:
        """Insert mapping between slide_id and FAISS vector_id."""
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO faiss_index (slide_id, vector_id) VALUES (%s, %s)",
                (slide_id, vector_id)
            )
            logger.debug(f"FAISS mapping inserted: slide={slide_id}, vector_id={vector_id}")
    
    @staticmethod
    def get_slide_by_id(slide_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve slide by ID."""
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                SELECT s.*, d.filename as deck_filename, d.original_path as deck_path
                FROM slides s
                JOIN decks d ON s.deck_id = d.deck_id
                WHERE s.slide_id = %s
                """,
                (slide_id,)
            )
            result = cur.fetchone()
            return dict(result) if result else None
    
    @staticmethod
    def get_slides_by_vector_ids(vector_ids: List[int]) -> List[Dict[str, Any]]:
        """Get slides corresponding to FAISS vector IDs."""
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                """
                SELECT s.*, d.filename as deck_filename, d.original_path as deck_path,
                       f.vector_id
                FROM slides s
                JOIN decks d ON s.deck_id = d.deck_id
                JOIN faiss_index f ON s.slide_id = f.slide_id
                WHERE f.vector_id = ANY(%s)
                """,
                (vector_ids,)
            )
            results = cur.fetchall()
            return [dict(row) for row in results]
    
    @staticmethod
    def get_all_decks() -> List[Dict[str, Any]]:
        """Retrieve all decks."""
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM decks ORDER BY uploaded_at DESC")
            results = cur.fetchall()
            return [dict(row) for row in results]
    
    @staticmethod
    def get_slides_by_deck_id(deck_id: str) -> List[Dict[str, Any]]:
        """Retrieve all slides for a deck."""
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT * FROM slides WHERE deck_id = %s ORDER BY slide_index",
                (deck_id,)
            )
            results = cur.fetchall()
            return [dict(row) for row in results]


# Global database instance
db = Database()
