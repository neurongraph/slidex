#!/usr/bin/env python3
"""
Rebuild the FAISS index from database records.
Useful when the index and database are out of sync.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.database import get_db_connection, db
from slidex.core.vector_index import vector_index
from slidex.core.ollama_client import ollama_client


def rebuild_index():
    """Rebuild FAISS index from all slides in the database."""
    
    logger.info("Rebuilding FAISS index from database...")
    
    try:
        # Get all decks
        decks = db.get_all_decks()
        logger.info(f"Found {len(decks)} decks in database")
        
        if not decks:
            print("No decks found in database. Nothing to rebuild.")
            return
        
        # Clear existing FAISS index
        logger.info("Creating new FAISS index...")
        vector_index._create_new_index()
        
        # Clear existing mappings
        logger.info("Clearing old vector mappings...")
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM faiss_index")
            conn.commit()
            cur.close()
        
        # Process all slides
        total_slides = 0
        processed_slides = 0
        
        for deck in decks:
            deck_id = str(deck['deck_id'])
            slides = db.get_slides_by_deck_id(deck_id)
            
            logger.info(f"Processing deck: {deck['filename']} ({len(slides)} slides)")
            print(f"\nProcessing: {deck['filename']}")
            
            for slide in slides:
                total_slides += 1
                
                # Reconstruct embedding input
                title = slide['title_header'] or ''
                plain_text = slide['plain_text'] or ''
                summary = slide['summary_10_20_words'] or ''
                embedding_input = f"{title}\n{plain_text}\n{summary}"
                
                try:
                    # Generate embedding
                    embedding = ollama_client.generate_embedding(
                        embedding_input[:2000],
                        session_id="rebuild"
                    )
                    
                    # Add to FAISS index
                    vector_id = vector_index.add_vector(embedding)
                    
                    # Update database mapping
                    db.insert_faiss_mapping(str(slide['slide_id']), vector_id)
                    
                    processed_slides += 1
                    print(f"  ✓ Slide {slide['slide_index'] + 1}: vector_id={vector_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing slide {slide['slide_id']}: {e}")
                    print(f"  ✗ Slide {slide['slide_index'] + 1}: {e}")
        
        # Save the index
        logger.info("Saving FAISS index...")
        vector_index.save()
        
        print(f"\n✓ Index rebuilt successfully!")
        print(f"  Total slides: {total_slides}")
        print(f"  Processed: {processed_slides}")
        print(f"  Failed: {total_slides - processed_slides}")
        
        # Show final stats
        stats = vector_index.get_stats()
        print(f"\n  FAISS index: {stats['total_vectors']} vectors")
        
    except Exception as e:
        logger.error(f"Error rebuilding index: {e}")
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    rebuild_index()
