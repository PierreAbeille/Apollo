"""Similarity computation utilities."""
import numpy as np
from typing import List, Tuple


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Args:
        vec_a: First vector
        vec_b: Second vector
        
    Returns:
        Cosine similarity score (0 to 1)
    """
    # Normalize vectors
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def cosine_similarity_matrix(vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between a vector and all vectors in a matrix.
    
    Args:
        vec: Single vector (embedding_dim,)
        matrix: Matrix of vectors (n_vectors, embedding_dim)
        
    Returns:
        Array of similarity scores (n_vectors,)
    """
    # Normalize query vector
    vec_norm = vec / np.linalg.norm(vec)
    
    # Normalize all matrix vectors
    matrix_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix_norms[matrix_norms == 0] = 1  # Avoid division by zero
    matrix_normalized = matrix / matrix_norms
    
    # Compute dot products
    similarities = np.dot(matrix_normalized, vec_norm)
    
    return similarities


def top_k_similar(
    query_vec: np.ndarray, 
    embeddings: np.ndarray, 
    k: int = 10,
    exclude_indices: List[int] = None
) -> List[Tuple[int, float]]:
    """
    Find top K most similar embeddings to query vector.
    
    Args:
        query_vec: Query embedding vector
        embeddings: Matrix of all embeddings
        k: Number of top results to return
        exclude_indices: Indices to exclude from results
        
    Returns:
        List of (index, similarity_score) tuples, sorted by score descending
    """
    # Compute all similarities
    similarities = cosine_similarity_matrix(query_vec, embeddings)
    
    # Exclude specified indices
    if exclude_indices:
        similarities[exclude_indices] = -np.inf
    
    # Get top K
    top_indices = np.argsort(similarities)[-k:][::-1]
    top_scores = similarities[top_indices]
    
    return list(zip(top_indices.tolist(), top_scores.tolist()))


def normalize_vector(vec: np.ndarray) -> np.ndarray:
    """
    Normalize a vector to unit length.
    
    Args:
        vec: Input vector
        
    Returns:
        Normalized vector
    """
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


def batch_normalize(matrix: np.ndarray) -> np.ndarray:
    """
    Normalize all vectors in a matrix.
    
    Args:
        matrix: Matrix of vectors (n_vectors, embedding_dim)
        
    Returns:
        Normalized matrix
    """
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1  # Avoid division by zero
    return matrix / norms
