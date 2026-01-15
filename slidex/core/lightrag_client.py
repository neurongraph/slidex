"""
LightRAG client wrapper for slidex.
Integrates LightRAG with Ollama models and audit logging.
"""

import asyncio
import time
import traceback
from typing import List, Optional, Dict, Any, Literal
import numpy as np

from lightrag import LightRAG, QueryParam
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import wrap_embedding_func_with_attrs
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.rerank import generic_rerank_api

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.audit_logger import audit_logger


class LightRAGClient:
    """Wrapper for LightRAG with Ollama integration and audit logging."""
    
    def __init__(self):
        """Initialize LightRAG client."""
        self.rag = None
        self._initialized = False
        
    async def _initialize_async(self) -> None:
        """Async initialization of LightRAG."""
        if self._initialized:
            return
            
        logger.info("Initializing LightRAG client...")
        
        # Create embedding function with audit logging wrapper
        @wrap_embedding_func_with_attrs(
            embedding_dim=768,  # nomic-embed-text dimension
            max_token_size=8192
        )
        async def embedding_func_with_audit(texts: List[str]) -> np.ndarray:
            """Embedding function with audit logging."""
            start_time = time.time()
            try:
                # Call ollama_embed with host configuration
                result = await ollama_embed(
                    texts,
                    embed_model=settings.ollama_embedding_model,
                    host=settings.ollama_base_url
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Log to audit database
                for text in texts:
                    audit_logger.log_llm_call(
                        model_name=settings.ollama_embedding_model,
                        operation_type="embedding_lightrag",
                        input_text=text[:500],
                        output_text=f"Vector dimension: 768",
                        metadata={"vector_dimension": 768},
                        duration_ms=duration_ms / len(texts),
                    )
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"Error in LightRAG embedding: {e}")
                
                # Log error
                audit_logger.log_llm_call(
                    model_name=settings.ollama_embedding_model,
                    operation_type="embedding_lightrag",
                    input_text=texts[0][:500] if texts else "",
                    error=str(e),
                    duration_ms=duration_ms,
                )
                raise
        
        # Create LLM function with audit logging wrapper
        async def llm_model_func_with_audit(
            prompt: str,
            system_prompt: Optional[str] = None,
            history_messages: List = [],
            **kwargs
        ) -> str:
            """LLM function with audit logging."""
            start_time = time.time()
            try:
                # Add host configuration to kwargs if not present
                if 'host' not in kwargs:
                    kwargs['host'] = settings.ollama_base_url
                
                # Call ollama_model_complete
                # Note: model_name comes from kwargs["hashing_kv"].global_config["llm_model_name"]
                # which is set during LightRAG initialization
                response = await ollama_model_complete(
                    prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    **kwargs
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Log to audit database
                audit_logger.log_llm_call(
                    model_name=settings.ollama_summary_model,
                    operation_type="llm_lightrag",
                    input_text=prompt[:500],
                    output_text=response[:500] if response else "",
                    metadata={"context_size": settings.lightrag_llm_context_size},
                    duration_ms=duration_ms,
                )
                
                return response
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"Error in LightRAG LLM call: {e}")
                
                # Log error
                audit_logger.log_llm_call(
                    model_name=settings.ollama_summary_model,
                    operation_type="llm_lightrag",
                    input_text=prompt[:500],
                    error=str(e),
                    duration_ms=duration_ms,
                )
                raise
        
        # Initialize LightRAG with optional vLLM reranker
        lightRAG_kwargs = {
            "working_dir": str(settings.lightrag_working_dir),
            "llm_model_func": llm_model_func_with_audit,
            "llm_model_name": settings.ollama_summary_model,
            "embedding_func": embedding_func_with_audit,
        }
        
        # Add vLLM reranker if enabled
        if settings.vllm_reranker_enabled:
            logger.info("Enabling vLLM-based reranker for LightRAG")
            
            async def vllm_rerank_func(
                query: str,
                documents: List[str],
                top_n: Optional[int] = None
            ) -> List[Dict[str, Any]]:
                """vLLM reranker function for LightRAG."""
                try:
                    # Call vLLM reranker API
                    results = await generic_rerank_api(
                        query=query,
                        documents=documents,
                        model=settings.vllm_reranker_model,
                        base_url=settings.vllm_reranker_url,
                        api_key=None,  # vLLM typically doesn't require API key
                        top_n=top_n,
                        response_format="standard"
                    )
                    return results
                except Exception as e:
                    logger.error(f"Error in vLLM reranker: {e}")
                    # Return default ranking if reranker fails
                    return [{"index": i, "relevance_score": 1.0 / (i + 1)} for i in range(len(documents))]
            
            # LightRAG currently expects `rerank_model_func` as the keyword
            lightRAG_kwargs["rerank_model_func"] = vllm_rerank_func
        
        # Initialize LightRAG
        self.rag = LightRAG(**lightRAG_kwargs)
        
        # Initialize storages
        await self.rag.initialize_storages()
        
        # Initialize pipeline status (required for insert operations)
        await initialize_pipeline_status()
        
        self._initialized = True
        logger.info("LightRAG client initialized successfully")
    
    def initialize(self) -> None:
        """Synchronous wrapper for initialization."""
        if not self._initialized:
            # Add timeout to prevent hanging during initialization
            try:
                import asyncio
                # Run with timeout to prevent hanging
                asyncio.run(asyncio.wait_for(self._initialize_async(), timeout=60.0))
            except asyncio.TimeoutError:
                logger.error("LightRAG initialization timed out")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize LightRAG: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
    
    def insert_document(
        self,
        text: str,
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Insert a document into LightRAG.
        
        Args:
            text: Document text content
            document_id: Unique document identifier (e.g., slide_id)
            metadata: Optional metadata dict
        """
        if not self._initialized:
            self.initialize()
        
        logger.debug(f"Inserting document into LightRAG: {document_id}")
        
        # Prepare document with metadata and explicit slide ID marker
        doc_text = text
        if metadata:
            # Prepend metadata as context
            meta_str = " | ".join([f"{k}: {v}" for k, v in metadata.items()])
            doc_text = f"[{meta_str}]\n{text}"
        
        # Add explicit slide ID marker for reliable extraction
        doc_text = f"[SLIDE_ID:{document_id}]\n{doc_text}"
        
        try:
            # Insert document with ID
            self.rag.insert(doc_text, ids=[document_id])
            logger.debug(f"Document inserted: {document_id}")
        except Exception as e:
            logger.error(f"Error inserting document {document_id}: {e}")
            raise
    
    def insert_documents_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> None:
        """
        Insert multiple documents in batch.
        
        Args:
            documents: List of dicts with 'text', 'id', and optional 'metadata' keys
        """
        if not self._initialized:
            self.initialize()
        
        texts = []
        ids = []
        
        for doc in documents:
            text = doc['text']
            doc_id = doc['id']
            metadata = doc.get('metadata')
            
            # Prepare document with metadata
            if metadata:
                meta_str = " | ".join([f"{k}: {v}" for k, v in metadata.items()])
                text = f"[{meta_str}]\n{text}"
            
            # Add explicit slide ID marker for reliable extraction
            text = f"[SLIDE_ID:{doc_id}]\n{text}"
            
            texts.append(text)
            ids.append(doc_id)
        
        logger.info(f"Batch inserting {len(documents)} documents into LightRAG")
        
        try:
            self.rag.insert(texts, ids=ids)
            logger.info(f"Batch insert complete: {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error in batch insert: {e}")
            raise
    
    def query(
        self,
        query_text: str,
        mode: Literal["naive", "local", "global", "hybrid"] = "hybrid",
        top_k: Optional[int] = None,
        include_references: bool = True
    ) -> Dict[str, Any]:
        """
        Query LightRAG for relevant documents.
        
        Args:
            query_text: Search query
            mode: Query mode (naive, local, global, hybrid)
            top_k: Number of results (currently LightRAG handles this internally)
            include_references: Whether to request source references from LightRAG
            
        Returns:
            Dict with 'response' (text) and optionally 'references' (list)
        """
        if not self._initialized:
            self.initialize()
        
        logger.info(f"Querying LightRAG: '{query_text}' (mode={mode}, include_references={include_references})")
        
        try:
            # Create query parameters with reference inclusion
            query_param = QueryParam(
                mode=mode,
                include_references=include_references,
                top_k=top_k if top_k else 40
            )
            
            # Execute query - LightRAG query is synchronous
            result = self.rag.query(query_text, param=query_param)
            
            # LightRAG may return enhanced response with references
            # Check if result contains reference information
            if isinstance(result, dict) and 'response' in result:
                logger.debug(f"Query complete with structured response")
                return result
            else:
                # Fallback: plain text response
                logger.debug(f"Query complete, result length: {len(result) if result else 0}")
                return {'response': result, 'references': None}
            
        except Exception as e:
            logger.error(f"Error querying LightRAG: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the LightRAG index.
        
        Returns:
            Dict with index statistics
        """
        if not self._initialized:
            self.initialize()
        
        try:
            # LightRAG doesn't have a direct stats method, but we can check the storage
            working_dir = settings.lightrag_working_dir
            
            stats = {
                "working_dir": str(working_dir),
                "initialized": self._initialized,
                "embedding_model": settings.ollama_embedding_model,
                "llm_model": settings.ollama_summary_model,
                "lightrag_enabled": settings.lightrag_enabled,
                "vllm_reranker_enabled": settings.vllm_reranker_enabled,
            }

            if settings.vllm_reranker_enabled:
                stats["vllm_reranker_url"] = settings.vllm_reranker_url
                stats["vllm_reranker_model"] = settings.vllm_reranker_model
            
            # Try to get storage info if available
            if working_dir.exists():
                stats["storage_size_mb"] = sum(
                    f.stat().st_size for f in working_dir.rglob("*") if f.is_file()
                ) / (1024 * 1024)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting LightRAG stats: {e}")
            return {"error": str(e)}


# Global LightRAG client instance (lazy initialization)
lightrag_client = LightRAGClient()
