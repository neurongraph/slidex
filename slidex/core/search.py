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
    async def search(
        query: str,
        top_k: Optional[int] = None,
        session_id: Optional[str] = None,
        mode: Literal["naive", "local", "global", "hybrid"] = "hybrid"
    ) -> Dict[str, Any]:
        """
        Search for slides matching the query.
        
        Args:
            query: Search query text
            top_k: Number of results to return (default from settings)
            session_id: Optional session ID for audit logging
            mode: Query mode for LightRAG (naive, local, global, hybrid)
            
        Returns:
            Dict with 'results' list and optional 'response' (markdown answer)
        """
        if top_k is None:
            top_k = settings.top_k_results
        
        logger.info(f"Searching for: '{query}' (top_k={top_k}, mode={mode})")
        
        try:
            # Use LightRAG if enabled, otherwise fall back to FAISS
            if settings.lightrag_enabled:
                return await SearchEngine._search_with_lightrag(query, top_k, mode)
            else:
                return {
                    'results': SearchEngine._search_with_faiss(query, top_k, session_id),
                    'response': None
                }
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
    async def _search_with_lightrag(
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
            
            # Use async aquery() method since we're in FastAPI's event loop
            logger.debug("Calling LightRAG async query")
            try:
                # Call the async aquery() method directly - no event loop conflicts
                context = await lightrag_client.rag.aquery(
                    query,
                    param=QueryParam(
                        mode=mode,
                        only_need_context=True,
                        top_k=top_k,
                        enable_rerank=False,
                    ),
                )
                logger.debug("LightRAG async query completed")
            except Exception as e:
                logger.error(f"Error in LightRAG query: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
            
            # Convert context to string if needed
            logger.debug(f"Converting context to string")
            if hasattr(context, 'text'):
                context = str(context.text)
            elif hasattr(context, '__str__'):
                context = str(context)
            else:
                context = str(context)
            
            logger.debug(f"LightRAG query completed, context length: {len(context) if context else 0}")

            
            if not context:
                logger.info("No context from LightRAG")
                return []
            
            logger.debug(f"LightRAG context length: {len(context)}")
            
            # Step 2: Extract [SLIDE_ID:uuid] markers from context
            logger.debug("Extracting slide IDs from context markers")
            marker_pattern = r'\[SLIDE_ID:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]'
            slide_ids = re.findall(marker_pattern, context, re.IGNORECASE)
            logger.debug(f"Found {len(slide_ids)} slide IDs in pattern")
            
            if not slide_ids:
                logger.warning("No slide IDs found in LightRAG context, falling back to FAISS")
                return SearchEngine._search_with_faiss(query, top_k)
            
            logger.info(f"Extracted {len(slide_ids)} slide IDs from context markers")
            
            # Remove duplicates while preserving order
            logger.debug("Removing duplicate slide IDs")
            seen = set()
            unique_slide_ids = []
            for sid in slide_ids:
                sid_lower = sid.lower()
                if sid_lower not in seen:
                    seen.add(sid_lower)
                    unique_slide_ids.append(sid_lower)
            
            # Limit to top_k
            unique_slide_ids = unique_slide_ids[:top_k]
            logger.debug(f"After dedup and limiting: {len(unique_slide_ids)} unique slide IDs")
            
            logger.info(f"Found {len(unique_slide_ids)} unique slide IDs from LightRAG")
            
            # Step 3: Generate natural language response from LightRAG
            logger.debug("Generating natural language answer from LightRAG")
            try:
                # Use LightRAG's async method to generate a markdown answer
                answer = await lightrag_client.rag.aquery(
                    f"Based on the context provided, answer this user question in markdown format: {query}",
                    param=QueryParam(
                        mode=mode,
                        only_need_context=False,  # Get full answer, not just context
                        top_k=top_k,
                        enable_rerank=False,
                    ),
                )
                # Convert answer to string if needed
                if hasattr(answer, 'text'):
                    response_text = str(answer.text)
                elif hasattr(answer, '__str__'):
                    response_text = str(answer)
                else:
                    response_text = str(answer)
                logger.debug(f"Generated answer length: {len(response_text)}")
            except Exception as e:
                logger.warning(f"Failed to generate answer: {e}")
                response_text = f"Found {len(unique_slide_ids)} relevant slides matching your query: '{query}'"
            
            # Step 4: Retrieve slide metadata from database
            logger.debug("Retrieving slide metadata from database")
            results = []
            for idx, slide_id in enumerate(unique_slide_ids):
                logger.debug(f"Fetching slide {idx+1}/{len(unique_slide_ids)}: {slide_id}")
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
                    }
                    results.append(result)
                else:
                    logger.warning(f"Slide not found in database: {slide_id}")
            
            if not results:
                logger.warning("No valid slides found, falling back to FAISS")
                fallback_results = SearchEngine._search_with_faiss(query, top_k)
                return {
                    'results': fallback_results,
                    'response': None
                }
            
            logger.info(f"Returning {len(results)} search results from LightRAG")
            return {
                'results': results,
                'response': response_text
            }
            
        except Exception as e:
            logger.error(f"Error searching with LightRAG: {e}")
            # Fallback to FAISS on error
            logger.warning("Falling back to FAISS search")
            fallback_results = SearchEngine._search_with_faiss(query, top_k)
            return {
                'results': fallback_results,
                'response': None
            }


# Global search engine instance
search_engine = SearchEngine()
