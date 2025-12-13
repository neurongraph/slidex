"""
Ollama client for generating embeddings and summaries.
All LLM interactions are logged to the audit database.
"""

import time
from typing import List, Optional
import ollama

from slidex.config import settings
from slidex.logging_config import logger
from slidex.core.audit_logger import audit_logger


class OllamaClient:
    """Client for interacting with Ollama for embeddings and text generation."""
    
    def __init__(self):
        """Initialize Ollama client."""
        self.client = ollama.Client(host=settings.ollama_base_url)
        self.embedding_model = settings.ollama_embedding_model
        self.summary_model = settings.ollama_summary_model
        logger.info(
            f"Ollama client initialized: embeddings={self.embedding_model}, "
            f"summary={self.summary_model}"
        )
    
    def generate_embedding(
        self,
        text: str,
        session_id: Optional[str] = None
    ) -> List[float]:
        """
        Generate embedding vector for the given text.
        
        Args:
            text: Input text to embed
            session_id: Optional session identifier for audit logging
            
        Returns:
            List of floats representing the embedding vector
        """
        start_time = time.time()
        error_msg = None
        embedding = None
        
        try:
            logger.debug(f"Generating embedding for text (length: {len(text)})")
            
            response = self.client.embeddings(
                model=self.embedding_model,
                prompt=text
            )
            
            embedding = response['embedding']
            duration_ms = (time.time() - start_time) * 1000
            
            logger.debug(
                f"Embedding generated: dimension={len(embedding)}, "
                f"duration={duration_ms:.2f}ms"
            )
            
            # Log to audit database
            audit_logger.log_llm_call(
                model_name=self.embedding_model,
                operation_type="embedding",
                input_text=text[:500],  # Store first 500 chars for audit
                output_text=f"Vector dimension: {len(embedding)}",
                session_id=session_id,
                metadata={"vector_dimension": len(embedding)},
                duration_ms=duration_ms,
            )
            
            return embedding
            
        except Exception as e:
            error_msg = str(e)
            duration_ms = (time.time() - start_time) * 1000
            
            logger.error(f"Error generating embedding: {e}")
            
            # Log error to audit database
            audit_logger.log_llm_call(
                model_name=self.embedding_model,
                operation_type="embedding",
                input_text=text[:500],
                session_id=session_id,
                error=error_msg,
                duration_ms=duration_ms,
            )
            
            raise
    
    def generate_summary(
        self,
        text: str,
        max_words: int = 20,
        session_id: Optional[str] = None
    ) -> str:
        """
        Generate a short summary of the text using Ollama LLM.
        
        Args:
            text: Input text to summarize
            max_words: Maximum number of words in summary (default 20)
            session_id: Optional session identifier for audit logging
            
        Returns:
            Summary text string
        """
        start_time = time.time()
        error_msg = None
        summary = None
        
        try:
            prompt = (
                f"Summarize the following slide content in exactly 10-20 words. "
                f"Be concise and capture the main point:\n\n{text[:1000]}"
            )
            
            logger.debug(f"Generating summary for text (length: {len(text)})")
            
            response = self.client.generate(
                model=self.summary_model,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": 50,  # Limit output tokens
                }
            )
            
            summary = response['response'].strip()
            duration_ms = (time.time() - start_time) * 1000
            
            logger.debug(
                f"Summary generated: length={len(summary)}, "
                f"duration={duration_ms:.2f}ms"
            )
            
            # Log to audit database
            audit_logger.log_llm_call(
                model_name=self.summary_model,
                operation_type="summary",
                input_text=prompt[:500],
                output_text=summary,
                session_id=session_id,
                metadata={"max_words": max_words, "summary_length": len(summary)},
                duration_ms=duration_ms,
            )
            
            return summary
            
        except Exception as e:
            error_msg = str(e)
            duration_ms = (time.time() - start_time) * 1000
            
            logger.error(f"Error generating summary: {e}")
            
            # Log error to audit database
            audit_logger.log_llm_call(
                model_name=self.summary_model,
                operation_type="summary",
                input_text=text[:500],
                session_id=session_id,
                error=error_msg,
                duration_ms=duration_ms,
            )
            
            raise


# Global Ollama client instance
ollama_client = OllamaClient()
