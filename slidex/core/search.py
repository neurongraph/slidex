"""
Search engine for semantic slide search using FAISS and Ollama embeddings.
"""

from typing import List, Dict, Any, Optional, Literal
import re
import traceback

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.ollama_client import ollama_client
from slidex.core.vector_index import vector_index
from slidex.core.database import db
from slidex.core.lightrag_client import lightrag_client


class SearchEngine:
    """Engine for searching slides using semantic search."""
    
    @staticmethod
    def search(
        query: str,
        top_k: Optional[int] = None,
        session_id: Optional[str] = None,
        mode: Literal["naive", "local", "global", "hybrid"] = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        Search for slides matching the query.
        
        Args:
            query: Search query text
            top_k: Number of results to return (default from settings)
            session_id: Optional session ID for audit logging
            mode: Query mode for LightRAG (naive, local, global, hybrid)
            
        Returns:
            List of search results with slide metadata and scores
        """
        if top_k is None:
            top_k = settings.top_k_results
        
        logger.info(f"Searching for: '{query}' (top_k={top_k}, mode={mode})")
        
        try:
            # Use LightRAG if enabled, otherwise fall back to FAISS
            if settings.lightrag_enabled:
                return SearchEngine._search_with_lightrag(query, top_k, mode)
            else:
                return SearchEngine._search_with_faiss(query, top_k, session_id)
        except Exception as e:
            logger.error(f"Error in search: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    @staticmethod
    def _search_with_faiss(
        query: str,
        top_k: int,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Original FAISS-based search."""
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
    
    @staticmethod
    def _search_with_lightrag(
        query: str,
        top_k: int,
        mode: str
    ) -> List[Dict[str, Any]]:
        """
        LightRAG-based search with context-aware retrieval.
        
        Strategy:
        1. Get raw context chunks from LightRAG (contains [SLIDE_ID:uuid] markers)
        2. Extract slide IDs from markers
        3. Generate natural language response for display
        4. Fallback to FAISS if extraction fails
        """
        try:
            # Step 1: Get raw context chunks with slide IDs
            from lightrag import QueryParam
            
            # Initialize LightRAG if not already done
            if not lightrag_client._initialized:
                lightrag_client.initialize()
            
            logger.debug("Retrieving context chunks from LightRAG")
            # Add timeout to prevent hanging
            try:
                # Execute query directly - LightRAG query is synchronous
                context = lightrag_client.rag.query(
                    query,
                    param=QueryParam(
                        mode=mode,
                        only_need_context=True,
                        top_k=top_k,
                        enable_rerank=False,
                    ),
                )
            except Exception as e:
                logger.error(f"Error in LightRAG query: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
            
            if not context:
                logger.info("No context from LightRAG")
                return []
            
            logger.debug(f"LightRAG context length: {len(context)}")
            
            # Step 2: Extract [SLIDE_ID:uuid] markers from context
            marker_pattern = r'\[SLIDE_ID:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]'
            slide_ids = re.findall(marker_pattern, context, re.IGNORECASE)
            
            if not slide_ids:
                logger.warning("No slide IDs found in LightRAG context, falling back to FAISS")
                return SearchEngine._search_with_faiss(query, top_k)
            
            logger.info(f"Extracted {len(slide_ids)} slide IDs from context markers")
            
            # Remove duplicates while preserving order
            seen = set()
            unique_slide_ids = []
            for sid in slide_ids:
                sid_lower = sid.lower()
                if sid_lower not in seen:
                    seen.add(sid_lower)
                    unique_slide_ids.append(sid_lower)
            
            # Limit to top_k
            unique_slide_ids = unique_slide_ids[:top_k]
            
            logger.info(f"Found {len(unique_slide_ids)} unique slide IDs from LightRAG")
            
            # Step 3: Generate natural language response (optional, for display)
            response_text = None
            try:
                logger.debug("Generating natural language response")
                response_result = lightrag_client.query(
                    query,
                    mode=mode,
                    top_k=top_k,
                    include_references=False
                )
                response_text = response_result.get('response', '') if isinstance(response_result, dict) else response_result
            except Exception as e:
                logger.warning(f"Error generating response text: {e}")
                response_text = f"Found {len(unique_slide_ids)} relevant slides for query: {query}"
            
            # Step 4: Retrieve slide metadata from database
            results = []
            for idx, slide_id in enumerate(unique_slide_ids):
                slide = db.get_slide_by_id(slide_id)
                if slide:
                    # Assign score based on position (earlier = higher score)
                    score = 1.0 - (idx / len(unique_slide_ids)) if len(unique_slide_ids) > 1 else 1.0
                    
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
                        'lightrag_response': response_text if idx == 0 else None,  # Include full response with first result
                    }
                    results.append(result)
                else:
                    logger.warning(f"Slide not found in database: {slide_id}")
            
            if not results:
                logger.warning("No valid slides found, falling back to FAISS")
                return SearchEngine._search_with_faiss(query, top_k)
            
            logger.info(f"Returning {len(results)} search results from LightRAG")
            return results
            
        except Exception as e:
            logger.error(f"Error searching with LightRAG: {e}")
            # Fallback to FAISS on error
            logger.warning("Falling back to FAISS search")
            return SearchEngine._search_with_faiss(query, top_k)


# Global search engine instance
search_engine = SearchEngine()
