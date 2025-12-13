"""
FAISS vector index manager for storing and searching slide embeddings.
"""

import faiss
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import pickle

from slidex.config import settings
from slidex.logging_config import logger


class VectorIndex:
    """Manages FAISS index for slide embeddings."""
    
    def __init__(self, dimension: int = 768):
        """
        Initialize vector index.
        
        Args:
            dimension: Dimension of the embedding vectors (default 768 for nomic-embed-text)
        """
        self.dimension = dimension
        self.index = None
        self.index_path = settings.faiss_index_path
        self.metadata_path = settings.faiss_index_path.with_suffix('.metadata')
        self.current_id = 0
        
        # Try to load existing index
        if self.index_path.exists():
            self.load()
        else:
            self._create_new_index()
    
    def _create_new_index(self) -> None:
        """Create a new FAISS index."""
        # Using IndexFlatL2 for exact search (good for smaller datasets)
        # For larger datasets, consider IndexIVFFlat or IndexHNSWFlat
        self.index = faiss.IndexFlatL2(self.dimension)
        self.current_id = 0
        logger.info(f"Created new FAISS index with dimension {self.dimension}")
    
    def add_vector(self, vector: List[float]) -> int:
        """
        Add a vector to the index.
        
        Args:
            vector: Embedding vector to add
            
        Returns:
            vector_id: The ID assigned to this vector
        """
        if self.index is None:
            self._create_new_index()
        
        # Convert to numpy array
        vec_array = np.array([vector], dtype=np.float32)
        
        # Add to index
        self.index.add(vec_array)
        
        vector_id = self.current_id
        self.current_id += 1
        
        logger.debug(f"Vector added to index: id={vector_id}")
        
        return vector_id
    
    def add_vectors_batch(self, vectors: List[List[float]]) -> List[int]:
        """
        Add multiple vectors to the index in batch.
        
        Args:
            vectors: List of embedding vectors
            
        Returns:
            List of vector IDs
        """
        if self.index is None:
            self._create_new_index()
        
        # Convert to numpy array
        vec_array = np.array(vectors, dtype=np.float32)
        
        # Add to index
        self.index.add(vec_array)
        
        # Assign IDs
        vector_ids = list(range(self.current_id, self.current_id + len(vectors)))
        self.current_id += len(vectors)
        
        logger.info(f"Batch of {len(vectors)} vectors added to index")
        
        return vector_ids
    
    def search(self, query_vector: List[float], k: int = 10) -> Tuple[List[float], List[int]]:
        """
        Search for similar vectors in the index.
        
        Args:
            query_vector: Query embedding vector
            k: Number of results to return
            
        Returns:
            Tuple of (distances, vector_ids)
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Index is empty, returning no results")
            return [], []
        
        # Convert to numpy array
        query_array = np.array([query_vector], dtype=np.float32)
        
        # Search
        distances, indices = self.index.search(query_array, min(k, self.index.ntotal))
        
        # Convert to lists
        distances_list = distances[0].tolist()
        indices_list = indices[0].tolist()
        
        logger.debug(f"Search completed: found {len(indices_list)} results")
        
        return distances_list, indices_list
    
    def save(self) -> None:
        """Save the index to disk."""
        if self.index is None:
            logger.warning("No index to save")
            return
        
        # Ensure directory exists
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, str(self.index_path))
        
        # Save metadata (current_id counter)
        metadata = {
            'current_id': self.current_id,
            'dimension': self.dimension,
        }
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        
        logger.info(f"Index saved to {self.index_path} ({self.index.ntotal} vectors)")
    
    def load(self) -> None:
        """Load the index from disk."""
        if not self.index_path.exists():
            logger.warning(f"Index file not found: {self.index_path}")
            self._create_new_index()
            return
        
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(self.index_path))
            
            # Load metadata
            if self.metadata_path.exists():
                with open(self.metadata_path, 'rb') as f:
                    metadata = pickle.load(f)
                    self.current_id = metadata.get('current_id', self.index.ntotal)
                    self.dimension = metadata.get('dimension', self.dimension)
            else:
                self.current_id = self.index.ntotal
            
            # Sync with database to avoid duplicate vector_ids
            # Query the database for the maximum vector_id to ensure we don't create duplicates
            try:
                from slidex.core.database import get_db_connection
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT MAX(vector_id) FROM faiss_index")
                    result = cur.fetchone()
                    max_vector_id = result[0] if result[0] is not None else -1
                    cur.close()
                    
                    # Set current_id to one more than the max existing vector_id
                    if max_vector_id >= self.current_id:
                        self.current_id = max_vector_id + 1
                        logger.debug(f"Synced current_id with database: {self.current_id}")
            except Exception as db_error:
                logger.warning(f"Could not sync with database: {db_error}")
                # Continue with the current_id from metadata
            
            logger.info(
                f"Index loaded from {self.index_path} "
                f"({self.index.ntotal} vectors, dimension={self.dimension}, current_id={self.current_id})"
            )
            
        except Exception as e:
            logger.error(f"Error loading index: {e}")
            self._create_new_index()
    
    def get_stats(self) -> dict:
        """Get index statistics."""
        if self.index is None:
            return {'total_vectors': 0, 'dimension': self.dimension}
        
        return {
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'current_id': self.current_id,
        }


# Global vector index instance
vector_index = VectorIndex()
