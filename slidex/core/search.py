"""
Search engine for semantic slide search using FAISS and Ollama embeddings.
"""

from typing import List, Dict, Any, Optional

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.ollama_client import ollama_client
from slidex.core.vector_index import vector_index
from slidex.core.database import db


class SearchEngine:
    """Engine for searching slides using semantic search."""
    
    @staticmethod
    def search(
        query: str,
        top_k: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for slides matching the query.
        
        Args:
            query: Search query text
            top_k: Number of results to return (default from settings)
            session_id: Optional session ID for audit logging
            
        Returns:
            List of search results with slide metadata and scores
        """
        if top_k is None:
            top_k = settings.top_k_results
        
        logger.info(f"Searching for: '{query}' (top_k={top_k})")
        
        # Generate embedding for query
        try:
            query_embedding = ollama_client.generate_embedding(
                query,
                session_id=session_id
            )
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise
        
        # Search FAISS index
        distances, vector_ids = vector_index.search(query_embedding, k=top_k)
        
        if not vector_ids:
            logger.info("No results found")
            return []
        
        logger.debug(f"Found {len(vector_ids)} results from FAISS")
        
        # Get slide metadata from database
        slides = db.get_slides_by_vector_ids(vector_ids)
        
        # Combine with scores
        results = []
        for i, slide in enumerate(slides):
            # Find matching vector_id to get the correct distance
            vector_id = slide.get('vector_id')
            try:
                idx = vector_ids.index(vector_id)
                distance = distances[idx]
                # Convert distance to similarity score (lower distance = higher similarity)
                # Using inverse distance as score
                score = 1.0 / (1.0 + distance)
            except (ValueError, IndexError):
                score = 0.0
            
            result = {
                'slide_id': slide['slide_id'],
                'deck_id': slide['deck_id'],
                'deck_filename': slide['deck_filename'],
                'deck_path': slide['deck_path'],
                'slide_index': slide['slide_index'],
                'title_header': slide['title_header'],
                'summary': slide['summary_10_20_words'],
                'plain_text_preview': slide['plain_text'][:200] if slide['plain_text'] else '',
                'thumbnail_path': slide['thumbnail_path'],
                'score': score,
                'distance': distance,
            }
            results.append(result)
        
        # Sort by score (highest first)
        results.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"Returning {len(results)} search results")
        
        return results


# Global search engine instance
search_engine = SearchEngine()
