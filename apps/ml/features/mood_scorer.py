"""
Mood Scorer Module

Computes mood-based scores for movie recommendations using Plutchik emotions.
Integrates with the XGBoost-based taste scoring for mood-aware reranking.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.emotions import (
    PRIMARY_ORDER,
    DYADS,
    PRESETS,
    MOOD_ALPHA,
    MIN_CONFIDENCE,
    apply_transformation,
    mood_to_primary_distribution,
    get_all_moods,
)


# Path to emotion vectors
EMOTIONS_PATH = Path(__file__).parent.parent / "data" / "emotions" / "movie_emotions.parquet"


def load_emotion_vectors() -> pd.DataFrame:
    """
    Load pre-computed emotion vectors for all movies.
    
    Returns:
        DataFrame with columns: tmdb_id, e_*, d_*, confidence, entropy
    """
    if not EMOTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Emotion vectors not found: {EMOTIONS_PATH}\n"
            "Run pipeline: python pipelines/05_build_emotion_vectors.py"
        )
    
    return pd.read_parquet(EMOTIONS_PATH)


def get_film_emotion_vector(
    emotions_df: pd.DataFrame, 
    tmdb_id: int
) -> Optional[np.ndarray]:
    """
    Get the 8D primary emotion vector for a film.
    
    Args:
        emotions_df: Emotions DataFrame
        tmdb_id: Film's TMDB ID
        
    Returns:
        8D numpy array or None if film not found
    """
    row = emotions_df[emotions_df["tmdb_id"] == tmdb_id]
    
    if row.empty:
        return None
    
    emo_cols = [f"e_{emo}" for emo in PRIMARY_ORDER]
    return row[emo_cols].values[0].astype(np.float32)


def get_film_confidence(
    emotions_df: pd.DataFrame, 
    tmdb_id: int
) -> float:
    """Get confidence score for a film."""
    row = emotions_df[emotions_df["tmdb_id"] == tmdb_id]
    
    if row.empty:
        return 0.0
    
    return float(row["confidence"].values[0])


def mood_to_target_vector(
    mood: str, 
    preset: str = "congruence"
) -> np.ndarray:
    """
    Convert user mood + preset to target emotion vector.
    
    Args:
        mood: Primary emotion or dyad (e.g., "sadness", "grief")
        preset: One of "congruence", "regulation", "stimulation"
        
    Returns:
        8D target vector over primary emotions
    """
    target_dict = apply_transformation(mood, preset)
    
    # Convert to vector in PRIMARY_ORDER
    return np.array([target_dict.get(emo, 0.0) for emo in PRIMARY_ORDER], dtype=np.float32)


def compute_mood_score(
    E_film: np.ndarray,
    E_target: np.ndarray,
    confidence: float,
    min_confidence: float = MIN_CONFIDENCE
) -> float:
    """
    Compute mood score for a film.
    
    mood_score = dot(E_film, E_target) × conf
    
    Args:
        E_film: Film's 8D emotion vector
        E_target: Target 8D emotion vector
        confidence: Film's confidence score
        min_confidence: Minimum confidence threshold
        
    Returns:
        Mood score [0, 1]
    """
    # Dot product gives alignment with target
    alignment = float(np.dot(E_film, E_target))
    
    # Weight by confidence (typed films get full weight)
    effective_conf = max(confidence, min_confidence)
    
    return alignment * effective_conf


def compute_mood_scores_batch(
    emotions_df: pd.DataFrame,
    tmdb_ids: List[int],
    mood: str,
    preset: str = "congruence"
) -> Dict[int, float]:
    """
    Compute mood scores for a batch of films.
    
    Args:
        emotions_df: Full emotions DataFrame
        tmdb_ids: List of TMDB IDs to score
        mood: User's current mood
        preset: Transformation preset
        
    Returns:
        Dictionary mapping tmdb_id → mood_score
    """
    E_target = mood_to_target_vector(mood, preset)
    
    # Filter to requested films
    df = emotions_df[emotions_df["tmdb_id"].isin(tmdb_ids)].copy()
    
    # Compute scores
    emo_cols = [f"e_{emo}" for emo in PRIMARY_ORDER]
    scores = {}
    
    for _, row in df.iterrows():
        E_film = row[emo_cols].values.astype(np.float32)
        conf = row["confidence"]
        
        score = compute_mood_score(E_film, E_target, conf)
        scores[int(row["tmdb_id"])] = score
    
    return scores


def rerank_with_mood(
    candidates: List[Tuple[int, float]],
    mood: str,
    preset: str = "congruence",
    alpha: float = MOOD_ALPHA,
    emotions_df: Optional[pd.DataFrame] = None
) -> List[Tuple[int, float]]:
    """
    Rerank candidates by combining taste score with mood score.
    
    final_score = taste_score + alpha × mood_score
    
    Args:
        candidates: List of (tmdb_id, taste_score) tuples
        mood: User's current mood (primary or dyad)
        preset: Transformation preset
        alpha: Weight of mood score (0-1)
        emotions_df: Optional pre-loaded emotions DataFrame
        
    Returns:
        Reranked list of (tmdb_id, final_score) tuples
    """
    if emotions_df is None:
        emotions_df = load_emotion_vectors()
    
    # Get mood scores for all candidates
    tmdb_ids = [c[0] for c in candidates]
    mood_scores = compute_mood_scores_batch(emotions_df, tmdb_ids, mood, preset)
    
    # Combine scores
    reranked = []
    for tmdb_id, taste_score in candidates:
        mood_score = mood_scores.get(tmdb_id, 0.0)
        
        # Normalize mood_score to similar range as taste_score
        # taste_score is typically 2-10, mood_score is 0-1
        # Scale mood_score to 0-2 range
        scaled_mood = mood_score * 2.0
        
        final_score = taste_score + alpha * scaled_mood
        reranked.append((tmdb_id, final_score))
    
    # Sort by final score
    reranked.sort(key=lambda x: x[1], reverse=True)
    
    return reranked


def filter_by_mood(
    candidates: List[Tuple[int, float]],
    mood: str,
    preset: str = "congruence",
    top_n: int = 100,
    emotions_df: Optional[pd.DataFrame] = None
) -> List[Tuple[int, float]]:
    """
    Filter candidates to those with highest mood alignment.
    
    Unlike rerank_with_mood, this returns only the top mood-aligned films,
    preserving the original taste_score ordering within that subset.
    
    Args:
        candidates: List of (tmdb_id, taste_score) tuples
        mood: User's current mood
        preset: Transformation preset
        top_n: Number of mood-aligned films to keep
        emotions_df: Optional pre-loaded emotions DataFrame
        
    Returns:
        Filtered list with high mood alignment
    """
    if emotions_df is None:
        emotions_df = load_emotion_vectors()
    
    # Get mood scores
    tmdb_ids = [c[0] for c in candidates]
    mood_scores = compute_mood_scores_batch(emotions_df, tmdb_ids, mood, preset)
    
    # Sort by mood score, take top N
    by_mood = sorted(
        [(tid, mood_scores.get(tid, 0.0)) for tid in tmdb_ids],
        key=lambda x: x[1],
        reverse=True
    )[:top_n]
    
    top_mood_ids = set(x[0] for x in by_mood)
    
    # Filter original candidates (preserves taste ordering)
    return [(tid, score) for tid, score in candidates if tid in top_mood_ids]


def get_dominant_emotion(
    emotions_df: pd.DataFrame, 
    tmdb_id: int
) -> Tuple[str, float]:
    """
    Get the dominant emotion for a film.
    
    Returns:
        Tuple of (emotion_name, score)
    """
    row = emotions_df[emotions_df["tmdb_id"] == tmdb_id]
    
    if row.empty:
        return ("unknown", 0.0)
    
    emo_cols = [f"e_{emo}" for emo in PRIMARY_ORDER]
    row_data = row.iloc[0]
    
    max_col = max(emo_cols, key=lambda c: row_data[c])
    max_score = row_data[max_col]
    
    return (max_col[2:], float(max_score))  # Remove "e_" prefix


# =============================================================================
# TESTS
# =============================================================================

def test_mood_to_target_vector():
    """Test target vector generation."""
    # Primary + congruence = identity
    target = mood_to_target_vector("sadness", "congruence")
    assert target[PRIMARY_ORDER.index("sadness")] == 1.0
    assert np.sum(target) == 1.0
    
    # Primary + regulation
    target = mood_to_target_vector("sadness", "regulation")
    assert target[PRIMARY_ORDER.index("joy")] == 0.6
    assert target[PRIMARY_ORDER.index("trust")] == 0.4
    
    print("✓ test_mood_to_target_vector passed")


def test_compute_mood_score():
    """Test mood score computation."""
    # Perfect alignment
    E_film = np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
    E_target = np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
    
    score = compute_mood_score(E_film, E_target, confidence=1.0)
    assert score == 1.0
    
    # No alignment
    E_target = np.array([0, 0, 0, 0, 1, 0, 0, 0], dtype=np.float32)
    score = compute_mood_score(E_film, E_target, confidence=1.0)
    assert score == 0.0
    
    # Low confidence
    E_target = np.array([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
    score = compute_mood_score(E_film, E_target, confidence=0.05)
    assert score == 0.1  # limited to MIN_CONFIDENCE
    
    print("✓ test_compute_mood_score passed")


def run_all_tests():
    """Run all tests."""
    print("\n🧪 Running mood scorer tests...\n")
    test_mood_to_target_vector()
    test_compute_mood_score()
    print("\n✅ All tests passed!\n")


if __name__ == "__main__":
    run_all_tests()
