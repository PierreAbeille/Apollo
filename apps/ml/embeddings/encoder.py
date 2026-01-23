"""Sentence-Transformers encoder wrapper."""
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer


class MovieEncoder:
    """Wrapper for Sentence-Transformers model."""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Initialize encoder with specified model.
        
        Args:
            model_name: HuggingFace model name
        """
        print(f"Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        print(f"✓ Model loaded (embedding dimension: {self.model.get_sentence_embedding_dimension()})")
    
    def encode(self, texts: List[str], batch_size: int = 32, show_progress: bool = True) -> np.ndarray:
        """
        Encode texts into embeddings.
        
        Args:
            texts: List of text strings to encode
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar
            
        Returns:
            numpy array of embeddings (n_texts, embedding_dim)
        """
        if not texts:
            return np.array([])
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def encode_single(self, text: str) -> np.ndarray:
        """
        Encode a single text.
        
        Args:
            text: Text string to encode
            
        Returns:
            numpy array embedding vector
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()
