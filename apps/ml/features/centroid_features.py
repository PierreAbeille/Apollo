"""
Multi-Centroid User Profile Features (V1.5).

Replaces single user_profile (average of positive embeddings) with a 
multi-centroid representation using KMeans clustering.

Features generated:
- cos_pos_c0, cos_pos_c1, ...: Cosine similarity to each positive centroid
- max_cos_pos: Maximum cosine similarity across all positive centroids
- min_cos_pos: Minimum cosine similarity across all positive centroids (V1.5)
- mean_cos_pos: Mean cosine similarity across all positive centroids (V1.5)
- cos_to_neg_center: Cosine similarity to negative centroid (V1.5)
- pos_neg_margin: max_cos_pos - cos_to_neg_center (V1.5)
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


def compute_negative_centroid(
    embeddings: np.ndarray,
    negative_tmdb_ids: List[int],
    tmdb_to_index: Dict[int, int]
) -> Optional[np.ndarray]:
    """
    Compute anti-centroid from negative movie embeddings (V1.5).
    
    The anti-centroid is the mean of all negatively-rated movie embeddings.
    This helps the model learn to avoid movies similar to disliked ones.
    
    Args:
        embeddings: Full embedding matrix (N x D)
        negative_tmdb_ids: List of tmdb_ids for negative (disliked) movies
        tmdb_to_index: Mapping from tmdb_id to embedding index
        
    Returns:
        Anti-centroid vector (D,) or None if no negative embeddings found
    """
    negative_indices = []
    for tmdb_id in negative_tmdb_ids:
        if tmdb_id in tmdb_to_index:
            negative_indices.append(tmdb_to_index[tmdb_id])
    
    if len(negative_indices) == 0:
        print("  ⚠ No negative embeddings found, skipping anti-centroid")
        return None
    
    negative_embeddings = embeddings[negative_indices]
    anti_centroid = np.mean(negative_embeddings, axis=0)
    
    print(f"  ✓ Computed anti-centroid from {len(negative_indices)} negative movies")
    return anti_centroid


def compute_centroid_features(
    movie_embedding: np.ndarray,
    centroids: np.ndarray,
    negative_centroid: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Compute cosine similarity features between a movie and all centroids (V1.5).
    
    Args:
        movie_embedding: Single movie embedding vector (D,)
        centroids: Positive centroid matrix (n_clusters x D)
        negative_centroid: Optional anti-centroid vector (D,) for V1.5 features
        
    Returns:
        Feature vector: [cos_c0, ..., cos_cN-1, max_cos, min_cos, mean_cos, cos_neg, margin]
    """
    # Normalize movie embedding
    movie_norm = np.linalg.norm(movie_embedding)
    if movie_norm == 0:
        n_base_features = len(centroids) + 4  # individual + max + min + mean + (neg, margin if available)
        if negative_centroid is not None:
            return np.zeros(n_base_features + 2)
        return np.zeros(n_base_features)
    movie_normalized = movie_embedding / movie_norm
    
    # Normalize centroids
    centroid_norms = np.linalg.norm(centroids, axis=1, keepdims=True)
    centroid_norms[centroid_norms == 0] = 1  # Avoid division by zero
    centroids_normalized = centroids / centroid_norms
    
    # Compute cosine similarities to positive centroids
    cosine_similarities = np.dot(centroids_normalized, movie_normalized)
    
    # V1.5: Extended statistics
    max_cos = np.max(cosine_similarities)
    min_cos = np.min(cosine_similarities)
    mean_cos = np.mean(cosine_similarities)
    
    # Build feature vector
    features = list(cosine_similarities) + [max_cos, min_cos, mean_cos]
    
    # V1.5: Negative centroid features
    if negative_centroid is not None:
        neg_norm = np.linalg.norm(negative_centroid)
        if neg_norm > 0:
            neg_normalized = negative_centroid / neg_norm
            cos_neg = float(np.dot(neg_normalized, movie_normalized))
        else:
            cos_neg = 0.0
        
        # Margin: how much closer to positives than negatives
        margin = max_cos - cos_neg
        features.extend([cos_neg, margin])
    
    return np.array(features, dtype=np.float32)


def compute_centroid_features_batch(
    embeddings: np.ndarray,
    tmdb_ids: List[int],
    tmdb_to_index: Dict[int, int],
    centroids: np.ndarray,
    negative_centroid: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Compute centroid features for a batch of movies (V1.5).
    
    Args:
        embeddings: Full embedding matrix (N x D)
        tmdb_ids: List of tmdb_ids to compute features for
        tmdb_to_index: Mapping from tmdb_id to embedding index
        centroids: Positive centroid matrix (n_clusters x D)
        negative_centroid: Optional anti-centroid vector (D,)
        
    Returns:
        Feature matrix (len(tmdb_ids) x n_features)
    """
    # Calculate number of features
    n_base = len(centroids) + 3  # cosines + max + min + mean
    n_features = n_base + 2 if negative_centroid is not None else n_base
    
    features = np.zeros((len(tmdb_ids), n_features))
    
    for i, tmdb_id in enumerate(tmdb_ids):
        if tmdb_id in tmdb_to_index:
            movie_emb = embeddings[tmdb_to_index[tmdb_id]]
            features[i] = compute_centroid_features(movie_emb, centroids, negative_centroid)
        # else: features remain zeros
    
    return features


def get_centroid_feature_names(
    n_clusters: int = DEFAULT_N_CLUSTERS,
    include_negative: bool = False
) -> List[str]:
    """
    Get feature names for centroid-based features (V1.5).
    
    Args:
        n_clusters: Number of positive clusters
        include_negative: Whether to include negative centroid features
        
    Returns:
        List of feature names
    """
    names = [f"cos_pos_c{i}" for i in range(n_clusters)]
    names.extend(["max_cos_pos", "min_cos_pos", "mean_cos_pos"])
    
    if include_negative:
        names.extend(["cos_to_neg_center", "pos_neg_margin"])
    
    return names


def save_centroids(
    centroids: np.ndarray,
    model_version: str,
    models_dir: str,
    negative_centroid: Optional[np.ndarray] = None
) -> str:
    """
    Save centroids to numpy files (V1.5).
    
    Args:
        centroids: Positive centroid matrix (n_clusters x D)
        model_version: Model version string
        models_dir: Directory to save centroids
        negative_centroid: Optional anti-centroid vector (D,)
        
    Returns:
        Path to saved positive centroids file
    """
    pos_filepath = Path(models_dir) / f"{model_version}_pos_centroids.npy"
    np.save(pos_filepath, centroids)
    
    if negative_centroid is not None:
        neg_filepath = Path(models_dir) / f"{model_version}_neg_centroid.npy"
        np.save(neg_filepath, negative_centroid)
        print(f"  💾 Saved negative centroid to {neg_filepath}")
    
    return str(pos_filepath)


def load_centroids(
    model_version: str, 
    models_dir: str,
    load_negative: bool = True
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Load centroids from numpy files (V1.5).
    
    Args:
        model_version: Model version string
        models_dir: Directory where centroids are saved
        load_negative: Whether to attempt loading negative centroid
        
    Returns:
        Tuple of (positive_centroids, negative_centroid or None)
    """
    pos_filepath = Path(models_dir) / f"{model_version}_pos_centroids.npy"
    positive_centroids = np.load(pos_filepath)
    
    negative_centroid = None
    if load_negative:
        neg_filepath = Path(models_dir) / f"{model_version}_neg_centroid.npy"
        if neg_filepath.exists():
            negative_centroid = np.load(neg_filepath)
            print(f"  ✓ Loaded negative centroid from {neg_filepath}")
    
    return positive_centroids, negative_centroid


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
    """Test feature computation for a single movie (V1.5)."""
    # Create mock centroids (3 clusters, 4 dimensions)
    centroids = np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
    ], dtype=np.float64)
    
    # Movie aligned with first centroid
    movie_emb = np.array([1, 0, 0, 0], dtype=np.float64)
    
    # Without negative centroid: 3 (cos) + 3 (max, min, mean) = 6 features
    features = compute_centroid_features(movie_emb, centroids)
    
    assert len(features) == 6, f"Expected 6 features (no neg), got {len(features)}"
    assert features[0] == 1.0, f"Expected cos_c0=1.0, got {features[0]}"
    assert features[3] == 1.0, f"Expected max_cos=1.0, got {features[3]}"  # max_cos_pos
    assert features[4] == 0.0, f"Expected min_cos=0.0, got {features[4]}"  # min_cos_pos
    
    # With negative centroid: 6 + 2 (neg, margin) = 8 features
    neg_centroid = np.array([-1, 0, 0, 0], dtype=np.float64)
    features_neg = compute_centroid_features(movie_emb, centroids, neg_centroid)
    
    assert len(features_neg) == 8, f"Expected 8 features (with neg), got {len(features_neg)}"
    assert features_neg[6] == -1.0, f"Expected cos_neg=-1.0, got {features_neg[6]}"  # cos_to_neg_center
    assert features_neg[7] == 2.0, f"Expected margin=2.0, got {features_neg[7]}"  # pos_neg_margin
    
    print("✓ test_compute_centroid_features passed")


def test_compute_centroid_features_batch():
    """Test batch feature computation (V1.5)."""
    np.random.seed(42)
    embeddings = np.random.randn(10, 8)
    centroids = np.random.randn(5, 8)
    
    tmdb_ids = [100, 200, 300]
    tmdb_to_index = {100: 0, 200: 1, 300: 2}
    
    # Without negative: 5 + 3 = 8 features
    features = compute_centroid_features_batch(
        embeddings, tmdb_ids, tmdb_to_index, centroids
    )
    
    assert features.shape == (3, 8), f"Expected (3, 8), got {features.shape}"
    print("✓ test_compute_centroid_features_batch passed")


def test_feature_names():
    """Test feature name generation (V1.5)."""
    # Without negative
    names = get_centroid_feature_names(n_clusters=5, include_negative=False)
    expected = ['cos_pos_c0', 'cos_pos_c1', 'cos_pos_c2', 'cos_pos_c3', 'cos_pos_c4', 
                'max_cos_pos', 'min_cos_pos', 'mean_cos_pos']
    assert names == expected, f"Expected {expected}, got {names}"
    
    # With negative
    names_neg = get_centroid_feature_names(n_clusters=5, include_negative=True)
    expected_neg = ['cos_pos_c0', 'cos_pos_c1', 'cos_pos_c2', 'cos_pos_c3', 'cos_pos_c4', 
                    'max_cos_pos', 'min_cos_pos', 'mean_cos_pos',
                    'cos_to_neg_center', 'pos_neg_margin']
    assert names_neg == expected_neg, f"Expected {expected_neg}, got {names_neg}"
    
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
