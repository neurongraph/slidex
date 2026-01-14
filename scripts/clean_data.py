#!/usr/bin/env python3
"""
Clean all data from the database and FAISS index.
This removes all decks, slides, and vectors but keeps the schema intact.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.database import get_db_connection
from slidex.core.vector_index import vector_index
import shutil


def clean_data(confirm: bool = False):
    """Clean all data from database and FAISS index."""
    
    if not confirm:
        print("⚠️  WARNING: This will delete ALL data!")
        print("  - All decks and slides from PostgreSQL")
        print("  - All vectors from FAISS index")
        print("  - All thumbnails")
        print("  - All individual slide files")
        print("  - LLM audit logs")
        print()
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Cancelled.")
            return
    
    logger.info("Cleaning all data...")
    
    try:
        # Clean PostgreSQL database
        logger.info("Cleaning PostgreSQL database...")
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Delete in order to respect foreign key constraints
            print("\n📊 Cleaning PostgreSQL database...")
            
            # Get counts before deletion
            cur.execute("SELECT COUNT(*) FROM faiss_index")
            faiss_mappings = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM slides")
            slides_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM decks")
            decks_count = cur.fetchone()[0]
            
            print(f"  Found: {decks_count} decks, {slides_count} slides, {faiss_mappings} vector mappings")
            
            # Delete data (cascades will handle related records)
            logger.info("Deleting FAISS index mappings...")
            cur.execute("DELETE FROM faiss_index")
            print("  ✓ Deleted FAISS index mappings")
            
            logger.info("Deleting slides...")
            cur.execute("DELETE FROM slides")
            print("  ✓ Deleted slides")
            
            logger.info("Deleting decks...")
            cur.execute("DELETE FROM decks")
            print("  ✓ Deleted decks")
            
            # Reset sequences
            logger.info("Resetting sequences...")
            cur.execute("ALTER SEQUENCE IF EXISTS faiss_index_id_seq RESTART WITH 1")
            
            conn.commit()
            cur.close()
        
        # Clean FAISS index
        logger.info("Cleaning FAISS index...")
        print("\n🔍 Cleaning FAISS index...")
        vector_index._create_new_index()
        vector_index.save()
        print("  ✓ FAISS index cleared and saved")
        
        # Clean thumbnails
        logger.info("Cleaning thumbnails...")
        print("\n🖼️  Cleaning thumbnails...")
        thumbnails_dir = settings.thumbnails_dir
        if thumbnails_dir.exists():
            # Delete all subdirectories (deck folders)
            for item in thumbnails_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
            print(f"  ✓ Deleted thumbnails from {thumbnails_dir}")
        
        # Clean individual slide files
        logger.info("Cleaning individual slide files...")
        print("\n📄 Cleaning individual slide files...")
        slides_dir = settings.slides_dir
        if slides_dir.exists():
            # Delete all files and subdirectories
            deleted_count = 0
            for item in slides_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                    deleted_count += 1
                elif item.is_file():
                    item.unlink()
                    deleted_count += 1
            print(f"  ✓ Deleted {deleted_count} individual slide files from {slides_dir}")
        
        # Clean audit logs (optional - keeping LLM audit trail)
        # Uncomment if you want to delete audit logs too
        # logger.info("Cleaning audit logs...")
        # print("\n📝 Cleaning audit logs...")
        # if settings.audit_db_path.exists():
        #     import sqlite3
        #     conn = sqlite3.connect(str(settings.audit_db_path))
        #     conn.execute("DELETE FROM llm_audit_log")
        #     conn.commit()
        #     conn.close()
        #     print("  ✓ Audit logs cleared")
        
        print("\n✅ All data cleaned successfully!")
        print("\nDatabase and index are now empty but schema is intact.")
        print("You can start fresh by ingesting new files.")
        
        logger.info("Data cleaning completed successfully")
        
    except Exception as e:
        logger.error(f"Error cleaning data: {e}")
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if --yes flag is provided
    confirm = "--yes" in sys.argv or "-y" in sys.argv
    clean_data(confirm)
