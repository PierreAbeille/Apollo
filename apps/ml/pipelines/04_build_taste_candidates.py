#!/usr/bin/env python3
"""
Pipeline 04: Build Taste Candidates

Expands candidate pool via TMDB /similar for highly-rated films,
calculates user taste profile, scores all candidates, and saves top N.
"""
import sys
import json
import time
from pathlib import Path
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    EMBEDDINGS_DIR,
    MIN_RATING_FOR_SIMILAR,
    SIMILAR_MOVIES_PER_FILM,
    MAX_TASTE_CANDIDATES,
    TMDB_RATE_LIMIT_DELAY,
    EMBEDDING_MODEL
)
from clients.db import DatabaseClient
from clients.tmdb import get_similar_movies, get_movie_recommendations
from features.preference_score import (
    calculate_user_profile,
    get_highly_rated_movies
)
from embeddings.similarity import cosine_similarity_matrix


class TasteCandidateBuilder:
    """Builds personalized movie recommendations."""
    
    def __init__(self):
        """Initialize builder."""
        self.db = DatabaseClient()
        
        # Load embeddings
        self.embeddings, self.tmdb_to_index, self.index_to_tmdb = self.load_embeddings()
        
        # Statistics
        self.stats = {
            "highly_rated": 0,
            "similar_fetched": 0,
            "unique_candidates": 0,
            "api_calls": 0,
            "top_candidates_saved": 0,
        }
    
    def load_embeddings(self):
        """
        Load embeddings and index mappings from disk.
        
        Returns:
            Tuple of (embeddings_matrix, tmdb_to_index_dict, index_to_tmdb_list)
        """
        embeddings_path = Path(EMBEDDINGS_DIR) / "movie_embeddings.npy"
        index_path = Path(EMBEDDINGS_DIR) / "tmdb_id_index.json"
        mapping_path = Path(EMBEDDINGS_DIR) / "tmdb_to_index.json"
        
        print(f"Loading embeddings from {EMBEDDINGS_DIR}...")
        
        embeddings = np.load(embeddings_path)
        
        with open(index_path, "r") as f:
            index_to_tmdb = json.load(f)
        
        with open(mapping_path, "r") as f:
            tmdb_to_index = {int(k): v for k, v in json.load(f).items()}
        
        print(f"✓ Loaded {embeddings.shape[0]} embeddings (dimension: {embeddings.shape[1]})")
        
        return embeddings, tmdb_to_index, index_to_tmdb
    
    def expand_candidate_pool(self, highly_rated_ids: list) -> set:
        """
        Expand candidate pool by fetching similar movies from TMDB.
        
        Args:
            highly_rated_ids: List of TMDB IDs for highly rated movies
            
        Returns:
            Set of all candidate TMDB IDs
        """
        candidates = set(highly_rated_ids)
        
        print(f"\nExpanding candidate pool from {len(highly_rated_ids)} highly-rated films...")
        print(f"Fetching {SIMILAR_MOVIES_PER_FILM} similar movies per film")
        
        for i, tmdb_id in enumerate(highly_rated_ids, 1):
            # Get movie title for logging
            movie = self.db.get_movie_by_tmdb_id(tmdb_id)
            title = movie['title'] if movie else f"ID:{tmdb_id}"
            
            print(f"  [{i}/{len(highly_rated_ids)}] {title}...", end=" ", flush=True)
            
            try:
                # Rate limit
                time.sleep(TMDB_RATE_LIMIT_DELAY)
                
                # Fetch similar movies
                similar = get_similar_movies(tmdb_id, language="en-US", page=1)
                self.stats["api_calls"] += 1
                
                similar_ids = [m['id'] for m in similar.get('results', [])[:SIMILAR_MOVIES_PER_FILM]]
                candidates.update(similar_ids)
                
                self.stats["similar_fetched"] += len(similar_ids)
                print(f"+{len(similar_ids)}")
                
            except Exception as e:
                print(f"✗ Error: {e}")
        
        self.stats["unique_candidates"] = len(candidates)
        print(f"\n✓ Expanded to {len(candidates)} unique candidates")
        
        return candidates
    
    def score_candidates(self, user_profile: np.ndarray, candidate_ids: set, exclude_ids: set) -> list:
        """
        Score all candidates based on user profile similarity.
        
        Args:
            user_profile: User taste profile vector
            candidate_ids: Set of candidate TMDB IDs
            exclude_ids: Set of TMDB IDs to exclude (already rated)
            
        Returns:
            List of (tmdb_id, score) tuples sorted by score descending
        """
        print("\nScoring candidates...")
        
        scored_candidates = []
        
        for tmdb_id in candidate_ids:
            # Skip if not in embeddings
            if tmdb_id not in self.tmdb_to_index:
                continue
            
            # Skip if already rated
            if tmdb_id in exclude_ids:
                continue
            
            # Get embedding and compute similarity
            idx = self.tmdb_to_index[tmdb_id]
            embedding = self.embeddings[idx]
            
            # Compute cosine similarity
            similarity = cosine_similarity_matrix(user_profile, embedding.reshape(1, -1))[0]
            
            scored_candidates.append((tmdb_id, float(similarity)))
        
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        print(f"✓ Scored {len(scored_candidates)} candidates")
        
        return scored_candidates
    
    def save_top_candidates(self, scored_candidates: list):
        """
        Save top N candidates to database.
        
        Args:
            scored_candidates: List of (tmdb_id, score) tuples
        """
        # Take top N
        top_candidates = scored_candidates[:MAX_TASTE_CANDIDATES]
        
        print(f"\nSaving top {len(top_candidates)} candidates to database...")
        
        # Clear existing candidates
        self.db.clear_taste_candidates()
        
        # Insert new candidates
        model_version = f"{EMBEDDING_MODEL}_v1"
        self.db.insert_taste_candidates(top_candidates, model_version)
        
        self.stats["top_candidates_saved"] = len(top_candidates)
        
        print(f"✓ Saved {len(top_candidates)} taste candidates")
        
        # Show top 10
        print("\nTop 10 recommendations:")
        for i, (tmdb_id, score) in enumerate(top_candidates[:10], 1):
            movie = self.db.get_movie_by_tmdb_id(tmdb_id)
            title = movie['title'] if movie else f"ID:{tmdb_id}"
            year = movie['release_year'] if movie and movie['release_year'] else "N/A"
            print(f"  {i:2}. {title} ({year}) - Score: {score:.3f}")
    
    def run(self):
        """Main taste candidate building process."""
        print("=" * 60)
        print("Pipeline 04: Build Taste Candidates")
        print("=" * 60)
        
        # Connect to database
        self.db.connect()
        
        # Get user interactions
        print("\nFetching user interactions...")
        interactions = self.db.get_all_interactions()
        print(f"✓ Found {len(interactions)} interactions")
        
        # Calculate user profile
        print("\nCalculating user taste profile...")
        user_profile = calculate_user_profile(
            interactions,
            self.embeddings,
            self.tmdb_to_index
        )
        print(f"✓ Profile vector norm: {np.linalg.norm(user_profile):.3f}")
        
        # Get highly rated movies
        highly_rated_ids = get_highly_rated_movies(interactions, MIN_RATING_FOR_SIMILAR)
        self.stats["highly_rated"] = len(highly_rated_ids)
        print(f"✓ Found {len(highly_rated_ids)} movies rated ≥{MIN_RATING_FOR_SIMILAR}")
        
        # Expand candidate pool
        candidate_ids = self.expand_candidate_pool(highly_rated_ids)
        
        # Get IDs to exclude (already rated)
        exclude_ids = {i['tmdb_id'] for i in interactions if i.get('rating') is not None}
        
        # Score candidates
        scored_candidates = self.score_candidates(user_profile, candidate_ids, exclude_ids)
        
        # Save top candidates
        self.save_top_candidates(scored_candidates)
        
        # Close database
        self.db.close()
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Highly rated films:       {self.stats['highly_rated']}")
        print(f"Similar movies fetched:   {self.stats['similar_fetched']}")
        print(f"Unique candidates:        {self.stats['unique_candidates']}")
        print(f"Candidates scored:        {len(scored_candidates)}")
        print(f"Top candidates saved:     {self.stats['top_candidates_saved']}")
        print(f"📡 TMDB API calls:        {self.stats['api_calls']}")
        print("=" * 60)


if __name__ == "__main__":
    builder = TasteCandidateBuilder()
    builder.run()
