"""
Multi-Centroid User Profile Features.

Replaces single user_profile (average of positive embeddings) with a 
multi-centroid representation using KMeans clustering.

Features generated:
- cos_pos_c0, cos_pos_c1, cos_pos_c2, cos_pos_c3, cos_pos_c4: Cosine similarity to each centroid
- max_cos_pos: Maximum cosine similarity across all centroids
"""
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from sklearn.cluster import KMeans

# Default configuration
DEFAULT_N_CLUSTERS = 5
DEFAULT_RANDOM_STATE = 42


def compute_positive_centroids(
    embeddings: np.ndarray,
    positive_tmdb_ids: List[int],
    tmdb_to_index: Dict[int, int],
    n_clusters: int = DEFAULT_N_CLUSTERS,
    random_state: int = DEFAULT_RANDOM_STATE
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute KMeans centroids from positive movie embeddings.
    
    Args:
        embeddings: Full embedding matrix (N x D)
        positive_tmdb_ids: List of tmdb_ids for positive (liked) movies
        tmdb_to_index: Mapping from tmdb_id to embedding index
        n_clusters: Number of clusters (default: 5)
        random_state: Random seed for reproducibility
        
    Returns:
        Tuple of:
        - centroids: (n_clusters x D) array of centroid vectors
        - positive_embeddings: (n_positives x D) array of positive embeddings used
        
    Raises:
        ValueError: If fewer positive embeddings than clusters
    """
    # Collect positive embeddings
    positive_indices = []
    for tmdb_id in positive_tmdb_ids:
        if tmdb_id in tmdb_to_index:
            positive_indices.append(tmdb_to_index[tmdb_id])
    
    if len(positive_indices) == 0:
        raise ValueError("No positive embeddings found in the provided mapping")
    
    positive_embeddings = embeddings[positive_indices]
    
    # Adjust n_clusters if fewer positives than requested clusters
    actual_n_clusters = min(n_clusters, len(positive_indices))
    
    if actual_n_clusters < n_clusters:
        print(f"  ⚠ Only {len(positive_indices)} positives, using {actual_n_clusters} clusters instead of {n_clusters}")
    
    # Fit KMeans
    kmeans = KMeans(
        n_clusters=actual_n_clusters,
        random_state=random_state,
        n_init=10
    )
    kmeans.fit(positive_embeddings)
    
    centroids = kmeans.cluster_centers_
    
    # If fewer clusters than requested, pad with zeros
    if actual_n_clusters < n_clusters:
        padding = np.zeros((n_clusters - actual_n_clusters, embeddings.shape[1]))
        centroids = np.vstack([centroids, padding])
    
    return centroids, positive_embeddings


def compute_centroid_features(
    movie_embedding: np.ndarray,
    centroids: np.ndarray
) -> np.ndarray:
    """
    Compute cosine similarity features between a movie and all centroids.
    
    Args:
        movie_embedding: Single movie embedding vector (D,)
        centroids: Centroid matrix (n_clusters x D)
        
    Returns:
        Feature vector: [cos_c0, cos_c1, ..., cos_cN-1, max_cos]
    """
    # Normalize movie embedding
    movie_norm = np.linalg.norm(movie_embedding)
    if movie_norm == 0:
        return np.zeros(len(centroids) + 1)
    movie_normalized = movie_embedding / movie_norm
    
    # Normalize centroids
    centroid_norms = np.linalg.norm(centroids, axis=1, keepdims=True)
    centroid_norms[centroid_norms == 0] = 1  # Avoid division by zero
    centroids_normalized = centroids / centroid_norms
    
    # Compute cosine similarities
    cosine_similarities = np.dot(centroids_normalized, movie_normalized)
    
    # Maximum similarity
    max_cos = np.max(cosine_similarities)
    
    # Return features: individual cosines + max
    return np.concatenate([cosine_similarities, [max_cos]])


def compute_centroid_features_batch(
    embeddings: np.ndarray,
    tmdb_ids: List[int],
    tmdb_to_index: Dict[int, int],
    centroids: np.ndarray
) -> np.ndarray:
    """
    Compute centroid features for a batch of movies.
    
    Args:
        embeddings: Full embedding matrix (N x D)
        tmdb_ids: List of tmdb_ids to compute features for
        tmdb_to_index: Mapping from tmdb_id to embedding index
        centroids: Centroid matrix (n_clusters x D)
        
    Returns:
        Feature matrix (len(tmdb_ids) x (n_clusters + 1))
    """
    n_features = len(centroids) + 1  # cosines + max
    features = np.zeros((len(tmdb_ids), n_features))
    
    for i, tmdb_id in enumerate(tmdb_ids):
        if tmdb_id in tmdb_to_index:
            movie_emb = embeddings[tmdb_to_index[tmdb_id]]
            features[i] = compute_centroid_features(movie_emb, centroids)
        # else: features remain zeros
    
    return features


def get_centroid_feature_names(n_clusters: int = DEFAULT_N_CLUSTERS) -> List[str]:
    """
    Get feature names for centroid-based features.
    
    Args:
        n_clusters: Number of clusters
        
    Returns:
        List of feature names: ['cos_pos_c0', ..., 'cos_pos_cN-1', 'max_cos_pos']
    """
    names = [f"cos_pos_c{i}" for i in range(n_clusters)]
    names.append("max_cos_pos")
    return names


def save_centroids(
    centroids: np.ndarray,
    model_version: str,
    models_dir: str
) -> str:
    """
    Save centroids to a numpy file.
    
    Args:
        centroids: Centroid matrix (n_clusters x D)
        model_version: Model version string
        models_dir: Directory to save centroids
        
    Returns:
        Path to saved file
    """
    filepath = Path(models_dir) / f"{model_version}_pos_centroids.npy"
    np.save(filepath, centroids)
    return str(filepath)


def load_centroids(model_version: str, models_dir: str) -> np.ndarray:
    """
    Load centroids from a numpy file.
    
    Args:
        model_version: Model version string
        models_dir: Directory where centroids are saved
        
    Returns:
        Centroid matrix (n_clusters x D)
    """
    filepath = Path(models_dir) / f"{model_version}_pos_centroids.npy"
    return np.load(filepath)


# ============================================================================
# Tests
# ============================================================================

def test_compute_positive_centroids():
    """Test centroid computation with mock data."""
    # Create mock embeddings (10 movies, 8 dimensions)
    np.random.seed(42)
    embeddings = np.random.randn(10, 8)
    
    # Define positive movies (indices 0, 2, 4, 6, 8)
    positive_tmdb_ids = [100, 200, 300, 400, 500]
    tmdb_to_index = {100: 0, 200: 2, 300: 4, 400: 6, 500: 8}
    
    centroids, pos_embs = compute_positive_centroids(
        embeddings, positive_tmdb_ids, tmdb_to_index, n_clusters=3
    )
    
    assert centroids.shape == (3, 8), f"Expected (3, 8), got {centroids.shape}"
    assert pos_embs.shape == (5, 8), f"Expected (5, 8), got {pos_embs.shape}"
    print("✓ test_compute_positive_centroids passed")


def test_compute_centroid_features():
    """Test feature computation for a single movie."""
    # Create mock centroids (3 clusters, 4 dimensions)
    centroids = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
    ], dtype=np.float64)
    
    # Movie aligned with first centroid
    movie_emb = np.array([1, 0, 0, 0], dtype=np.float64)
    
    features = compute_centroid_features(movie_emb, centroids)
    
    assert len(features) == 4, f"Expected 4 features, got {len(features)}"
    assert features[0] == 1.0, f"Expected cos_c0=1.0, got {features[0]}"
    assert features[3] == 1.0, f"Expected max_cos=1.0, got {features[3]}"
    print("✓ test_compute_centroid_features passed")


def test_compute_centroid_features_batch():
    """Test batch feature computation."""
    np.random.seed(42)
    embeddings = np.random.randn(10, 8)
    centroids = np.random.randn(5, 8)
    
    tmdb_ids = [100, 200, 300]
    tmdb_to_index = {100: 0, 200: 1, 300: 2}
    
    features = compute_centroid_features_batch(
        embeddings, tmdb_ids, tmdb_to_index, centroids
    )
    
    assert features.shape == (3, 6), f"Expected (3, 6), got {features.shape}"
    print("✓ test_compute_centroid_features_batch passed")


def test_feature_names():
    """Test feature name generation."""
    names = get_centroid_feature_names(n_clusters=5)
    expected = ['cos_pos_c0', 'cos_pos_c1', 'cos_pos_c2', 'cos_pos_c3', 'cos_pos_c4', 'max_cos_pos']
    assert names == expected, f"Expected {expected}, got {names}"
    print("✓ test_feature_names passed")


def test_fewer_positives_than_clusters():
    """Test handling of fewer positives than requested clusters."""
    np.random.seed(42)
    embeddings = np.random.randn(10, 8)
    
    # Only 2 positive movies, but requesting 5 clusters
    positive_tmdb_ids = [100, 200]
    tmdb_to_index = {100: 0, 200: 1}
    
    centroids, _ = compute_positive_centroids(
        embeddings, positive_tmdb_ids, tmdb_to_index, n_clusters=5
    )
    
    # Should pad to 5 clusters
    assert centroids.shape == (5, 8), f"Expected (5, 8), got {centroids.shape}"
    # Last 3 should be zeros
    assert np.allclose(centroids[2:], 0), "Padding centroids should be zeros"
    print("✓ test_fewer_positives_than_clusters passed")


def run_all_tests():
    """Run all tests."""
    print("\n🧪 Running centroid features tests...\n")
    test_compute_positive_centroids()
    test_compute_centroid_features()
    test_compute_centroid_features_batch()
    test_feature_names()
    test_fewer_positives_than_clusters()
    print("\n✅ All tests passed!\n")


if __name__ == "__main__":
    run_all_tests()
