"""
MMR Reranker - Maximal Marginal Relevance (V1.5).

Reranks candidates to balance relevance (model score) with diversity.
Prevents the top-N recommendations from being too similar to each other.

Algorithm:
    MMR(d) = λ × Score(d) - (1-λ) × max(Sim(d, already_selected))
    
    where λ controls the trade-off:
    - λ = 1.0: Pure relevance (no diversity)
    - λ = 0.0: Pure diversity (ignore scores)
    - λ = 0.7: Balanced (default, 70% relevance, 30% diversity)
"""
import numpy as np
from typing import List, Tuple, Dict, Optional


def mmr_rerank(
    candidates: List[Tuple[int, float]],
    embeddings: np.ndarray,
    tmdb_to_index: Dict[int, int],
    top_k: int = 200,
    lambda_param: float = 0.7
) -> List[Tuple[int, float]]:
    """
    Rerank candidates using Maximal Marginal Relevance.
    
    Greedy selection algorithm:
    1. Select the highest-scoring candidate
    2. For each remaining candidate, compute:
       MMR = λ × score - (1-λ) × max_similarity_to_selected
    3. Select the candidate with highest MMR
    4. Repeat until top_k candidates are selected
    
    Args:
        candidates: List of (tmdb_id, score) tuples, sorted by score descending
        embeddings: Full embedding matrix (N x D)
        tmdb_to_index: Mapping from tmdb_id to embedding index
        top_k: Number of candidates to return after reranking
        lambda_param: Diversity parameter (0.0-1.0)
        
    Returns:
        Reranked list of (tmdb_id, score) tuples
    """
    if len(candidates) <= 1:
        return candidates
    
    # Limit to reasonable pool size for efficiency
    pool_size = min(len(candidates), top_k * 3)
    pool = candidates[:pool_size]
    
    # Precompute embeddings for pool
    pool_embeddings = []
    valid_indices = []
    for i, (tmdb_id, score) in enumerate(pool):
        if tmdb_id in tmdb_to_index:
            emb = embeddings[tmdb_to_index[tmdb_id]]
            pool_embeddings.append(emb / (np.linalg.norm(emb) + 1e-8))  # Normalize
            valid_indices.append(i)
    
    if len(valid_indices) == 0:
        return candidates[:top_k]
    
    pool_embeddings = np.array(pool_embeddings)
    
    # Map valid_indices back to pool items
    valid_items = [(pool[i][0], pool[i][1], j) for j, i in enumerate(valid_indices)]
    # valid_items: (tmdb_id, score, embedding_index)
    
    # Normalize scores to [0, 1] for fair combination with similarity
    scores = np.array([item[1] for item in valid_items])
    if scores.max() > scores.min():
        normalized_scores = (scores - scores.min()) / (scores.max() - scores.min())
    else:
        normalized_scores = np.ones_like(scores)
    
    # Greedy MMR selection
    selected = []
    selected_emb_indices = []
    remaining = list(range(len(valid_items)))
    
    # Start with highest-scoring item
    best_idx = np.argmax(normalized_scores)
    selected.append(valid_items[best_idx])
    selected_emb_indices.append(valid_items[best_idx][2])
    remaining.remove(best_idx)
    
    # Iteratively select based on MMR
    while len(selected) < top_k and len(remaining) > 0:
        best_mmr = float('-inf')
        best_candidate = None
        best_remaining_idx = None
        
        for idx in remaining:
            tmdb_id, score, emb_idx = valid_items[idx]
            norm_score = normalized_scores[idx]
            
            # Compute max similarity to already selected items
            candidate_emb = pool_embeddings[emb_idx]
            selected_embs = pool_embeddings[selected_emb_indices]
            similarities = np.dot(selected_embs, candidate_emb)
            max_sim = np.max(similarities)
            
            # MMR formula
            mmr = lambda_param * norm_score - (1 - lambda_param) * max_sim
            
            if mmr > best_mmr:
                best_mmr = mmr
                best_candidate = (tmdb_id, score, emb_idx)
                best_remaining_idx = idx
        
        if best_candidate is not None:
            selected.append(best_candidate)
            selected_emb_indices.append(best_candidate[2])
            remaining.remove(best_remaining_idx)
    
    # Return as (tmdb_id, score) tuples
    result = [(tmdb_id, score) for tmdb_id, score, _ in selected]
    
    # If we need more items, append remaining unselected ones
    if len(result) < top_k:
        selected_tmdb_ids = set(r[0] for r in result)
        for tmdb_id, score in candidates:
            if tmdb_id not in selected_tmdb_ids:
                result.append((tmdb_id, score))
                if len(result) >= top_k:
                    break
    
    return result


def compute_diversity_score(
    candidates: List[Tuple[int, float]],
    embeddings: np.ndarray,
    tmdb_to_index: Dict[int, int],
    top_n: int = 10
) -> float:
    """
    Compute average pairwise diversity for top-N candidates.
    
    Diversity = 1 - average_pairwise_similarity
    
    Args:
        candidates: List of (tmdb_id, score) tuples
        embeddings: Full embedding matrix
        tmdb_to_index: Mapping from tmdb_id to embedding index
        top_n: Number of top candidates to consider
        
    Returns:
        Diversity score (0.0 = identical, 1.0 = maximally diverse)
    """
    top_items = candidates[:top_n]
    
    # Collect embeddings
    embs = []
    for tmdb_id, _ in top_items:
        if tmdb_id in tmdb_to_index:
            emb = embeddings[tmdb_to_index[tmdb_id]]
            embs.append(emb / (np.linalg.norm(emb) + 1e-8))
    
    if len(embs) < 2:
        return 1.0  # Can't compute diversity with < 2 items
    
    embs = np.array(embs)
    
    # Compute pairwise similarities
    sim_matrix = np.dot(embs, embs.T)
    
    # Get upper triangle (excluding diagonal)
    n = len(embs)
    total_sim = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total_sim += sim_matrix[i, j]
            count += 1
    
    avg_similarity = total_sim / count if count > 0 else 0.0
    diversity = 1.0 - avg_similarity
    
    return diversity


# ============================================================================
# Tests
# ============================================================================

def test_mmr_rerank():
    """Test MMR reranking with mock data."""
    np.random.seed(42)
    
    # Create mock embeddings (10 movies)
    embeddings = np.random.randn(10, 8)
    tmdb_to_index = {100 + i: i for i in range(10)}
    
    # Create candidates sorted by score
    candidates = [(100 + i, 10.0 - i * 0.5) for i in range(10)]
    
    # Rerank
    reranked = mmr_rerank(
        candidates,
        embeddings,
        tmdb_to_index,
        top_k=5,
        lambda_param=0.7
    )
    
    assert len(reranked) == 5, f"Expected 5 items, got {len(reranked)}"
    assert reranked[0][0] == 100, "First item should still be highest scorer"
    print("✓ test_mmr_rerank passed")


def test_diversity_score():
    """Test diversity score computation."""
    np.random.seed(42)
    
    # Create two groups of similar embeddings
    embeddings = np.vstack([
        np.random.randn(5, 8) + [1, 0, 0, 0, 0, 0, 0, 0],  # Cluster 1
        np.random.randn(5, 8) + [-1, 0, 0, 0, 0, 0, 0, 0],  # Cluster 2
    ])
    tmdb_to_index = {100 + i: i for i in range(10)}
    
    # Candidates from same cluster (low diversity)
    same_cluster = [(100 + i, 10.0 - i) for i in range(5)]
    div_same = compute_diversity_score(same_cluster, embeddings, tmdb_to_index, top_n=5)
    
    # Candidates from both clusters (higher diversity)
    mixed = [(100, 10.0), (105, 9.5), (101, 9.0), (106, 8.5), (102, 8.0)]
    div_mixed = compute_diversity_score(mixed, embeddings, tmdb_to_index, top_n=5)
    
    assert div_mixed > div_same, f"Mixed should be more diverse: {div_mixed} vs {div_same}"
    print("✓ test_diversity_score passed")


def run_all_tests():
    """Run all tests."""
    print("\n🧪 Running MMR reranker tests...\n")
    test_mmr_rerank()
    test_diversity_score()
    print("\n✅ All tests passed!\n")


if __name__ == "__main__":
    run_all_tests()
