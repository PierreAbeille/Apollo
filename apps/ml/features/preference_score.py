"""User preference scoring utilities."""
from typing import Dict, Any
import numpy as np


def get_preference_weight(rating: float = None, is_wishlisted: bool = False, is_recommended: bool = False) -> float:
    """
    Calculate preference weight for a user interaction.
    
    Higher ratings and recommendations get higher weights.
    Wishlist items get a small positive weight.
    
    Args:
        rating: User rating (1-10)
        is_wishlisted: Whether movie is wishlisted
        is_recommended: Whether movie is recommended by user
        
    Returns:
        Preference weight (0.0 to 1.0)
    """
    # If rated, use rating as base
    if rating is not None:
        # Normalize rating from [1,10] to [0,1]
        base_weight = (rating - 1) / 9
        
        # Boost recommended movies
        if is_recommended:
            base_weight = min(1.0, base_weight * 1.2)
        
        return base_weight
    
    # If wishlisted but not rated, give moderate weight
    if is_wishlisted:
        return 0.6
    
    # If recommended but not rated (edge case)
    if is_recommended:
        return 0.7
    
    # No preference signal
    return 0.0


def calculate_user_profile(
    interactions: list,
    embeddings: np.ndarray,
    tmdb_to_index: Dict[int, int]
) -> np.ndarray:
    """
    Calculate user taste profile as weighted average of embeddings.
    
    Args:
        interactions: List of interaction records with tmdb_id, rating, etc.
        embeddings: Full embedding matrix (n_movies, embedding_dim)
        tmdb_to_index: Mapping from tmdb_id to embedding index
        
    Returns:
        User profile vector (embedding_dim,)
    """
    weighted_embeddings = []
    total_weight = 0.0
    
    for interaction in interactions:
        tmdb_id = interaction['tmdb_id']
        
        # Skip if movie not in embeddings
        if tmdb_id not in tmdb_to_index:
            continue
        
        # Get preference weight
        weight = get_preference_weight(
            rating=interaction.get('rating'),
            is_wishlisted=interaction.get('is_wishlisted', False),
            is_recommended=interaction.get('is_recommended', False)
        )
        
        # Skip movies with no preference signal
        if weight <= 0:
            continue
        
        # Get embedding
        idx = tmdb_to_index[tmdb_id]
        embedding = embeddings[idx]
        
        # Add weighted embedding
        weighted_embeddings.append(embedding * weight)
        total_weight += weight
    
    if not weighted_embeddings or total_weight == 0:
        # Return zero vector if no preferences
        return np.zeros(embeddings.shape[1])
    
    # Calculate weighted average
    user_profile = np.sum(weighted_embeddings, axis=0) / total_weight
    
    return user_profile


def get_highly_rated_movies(interactions: list, min_rating: float = 8.0) -> list:
    """
    Filter interactions to get highly rated movies.
    
    Args:
        interactions: List of interaction records
        min_rating: Minimum rating threshold
        
    Returns:
        List of tmdb_ids for highly rated movies
    """
    highly_rated = []
    
    for interaction in interactions:
        rating = interaction.get('rating')
        if rating is not None and rating >= min_rating:
            highly_rated.append(interaction['tmdb_id'])
    
    return highly_rated
