#!/usr/bin/env python3
"""
Pipeline 04a: Build Candidate Pool

Extracts the TMDb Similar expansion logic from the original Pipeline 04.
Generates a pool of candidate movies for scoring by XGBoost.

Output: data/cache/candidate_pool.json
"""
import sys
import json
import time
from pathlib import Path
from typing import Set, List, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    CACHE_DIR,
    MIN_RATING_FOR_SIMILAR,
    SIMILAR_MOVIES_PER_FILM,
    TMDB_RATE_LIMIT_DELAY,
    EMBEDDING_MODEL,
    EMBEDDINGS_DIR,
)
from clients.db import DatabaseClient
from clients.tmdb import get_similar_movies, get_movie_details
from features.preference_score import get_highly_rated_movies
from features.text_builder import extract_movie_metadata, build_text_for_embedding


# Output path
CANDIDATE_POOL_PATH = Path(CACHE_DIR) / "candidate_pool.json"


class CandidatePoolBuilder:
    """Builds a pool of candidate movies from TMDb Similar expansion."""

    def __init__(self):
        """Initialize builder."""
        self.db = DatabaseClient()
        
        # Statistics
        self.stats = {
            "highly_rated": 0,
            "similar_fetched": 0,
            "unique_candidates": 0,
            "new_movies_processed": 0,
            "api_calls": 0,
        }

    def get_user_interactions(self) -> tuple:
        """
        Get user interactions and extract seen vs watchlist IDs.
        
        Returns:
            Tuple of (interactions, seen_ids, watchlist_ids)
        """
        interactions = self.db.get_all_interactions()
        
        # Seen: rated OR is_done=True
        seen_ids = {
            i["tmdb_id"] for i in interactions 
            if i.get("rating") is not None or i.get("is_done")
        }
        
        # Watchlist: is_wishlisted=True AND NOT seen
        watchlist_ids = {
            i["tmdb_id"] for i in interactions 
            if i.get("is_wishlisted") and i["tmdb_id"] not in seen_ids
        }
        
        return interactions, seen_ids, watchlist_ids

    def expand_candidate_pool(self, highly_rated_ids: List[int]) -> Set[int]:
        """
        Fetch similar movies via TMDB for each highly rated film.
        
        Args:
            highly_rated_ids: List of tmdb_ids for films rated >= MIN_RATING_FOR_SIMILAR
            
        Returns:
            Set of candidate tmdb_ids
        """
        candidates = set()
        print(f"\n🎯 Expanding candidate pool from {len(highly_rated_ids)} seed films...")
        
        for i, tmdb_id in enumerate(highly_rated_ids, 1):
            try:
                time.sleep(TMDB_RATE_LIMIT_DELAY)
                similar = get_similar_movies(tmdb_id, language="en-US", page=1)
                self.stats["api_calls"] += 1
                
                sim_ids = [m["id"] for m in similar.get("results", [])[:SIMILAR_MOVIES_PER_FILM]]
                candidates.update(sim_ids)
                self.stats["similar_fetched"] += len(sim_ids)
                
                if i % 5 == 0:
                    print(f"  [{i}/{len(highly_rated_ids)}] Processed... ({len(candidates)} candidates so far)")
            except Exception as e:
                print(f"  ✗ Error fetching similar for {tmdb_id}: {e}")
                
        print(f"✓ Found {len(candidates)} unique candidate TMDb IDs")
        return candidates

    def ensure_movie_features(self, candidate_ids: Set[int], exclude_ids: Set[int]) -> None:
        """
        Ensure all candidates have movie_features in DB.
        Fetch from TMDB if missing.
        
        Args:
            candidate_ids: Set of candidate tmdb_ids
            exclude_ids: Set of tmdb_ids to exclude (already rated)
        """
        # Filter out already rated
        discovery_pool = candidate_ids - exclude_ids
        print(f"\n📊 Discovery pool: {len(discovery_pool)} movies (excluding rated films)")

        # Check which movies need features
        print("Checking which movies need TMDB data...")
        existing_feats = {
            r['tmdb_id'] 
            for r in self.db.fetch_all("SELECT tmdb_id FROM movie_features")
        }
        
        to_fetch = [tid for tid in discovery_pool if tid not in existing_feats]
        
        if not to_fetch:
            print("✓ All candidates already have features in database.")
            return

        print(f"🔄 Fetching metadata for {len(to_fetch)} movies from TMDB...")
        
        for i, tmdb_id in enumerate(to_fetch, 1):
            try:
                time.sleep(TMDB_RATE_LIMIT_DELAY)
                
                # Optimized call: All-in-one with append_to_response
                data = get_movie_details(
                    tmdb_id, 
                    language="en-US", 
                    append_to_response="credits,keywords"
                )
                self.stats["api_calls"] += 1
                
                # Basic info for movies table
                release_date = data.get("release_date", "")
                release_year = int(release_date[:4]) if release_date else None
                
                self.db.upsert_movie(
                    tmdb_id, 
                    data.get("title", "Unknown"), 
                    release_year, 
                    data.get("poster_path")
                )
                
                # Build features for movie_features table
                metadata = extract_movie_metadata(
                    data, 
                    data.get("credits", {}), 
                    {"keywords": data.get("keywords", {}).get("keywords", [])}
                )
                
                text = build_text_for_embedding(
                    overview=metadata["overview"],
                    genres=metadata["genres"],
                    keywords=metadata["keywords"],
                    cast=metadata["cast"],
                    director=metadata["director"],
                    lang="en"
                )
                
                self.db.upsert_movie_features(
                    tmdb_id=tmdb_id,
                    lang="en",
                    overview=metadata["overview"],
                    keywords=data.get("keywords", {}).get("keywords", []),
                    genres=data.get("genres", []),
                    cast=data.get("credits", {}).get("cast", [])[:10],
                    crew=metadata["crew"],
                    production_countries=metadata["production_countries"],
                    popularity=metadata["popularity"],
                    vote_average=metadata["vote_average"],
                    vote_count=metadata["vote_count"],
                    text_for_embedding=text
                )
                
                self.stats["new_movies_processed"] += 1
                
                if i % 10 == 0:
                    print(f"  [{i}/{len(to_fetch)}] {data.get('title', 'Unknown')}... saved.")

            except Exception as e:
                print(f"  ✗ Error on ID {tmdb_id}: {e}")
                time.sleep(5)  # Backoff on error

    def save_candidate_pool(self, candidate_ids: Set[int], exclude_ids: Set[int]) -> None:
        """
        Save the candidate pool to a JSON file.
        
        Args:
            candidate_ids: Set of all candidate tmdb_ids
            exclude_ids: Set of tmdb_ids to exclude (already rated)
        """
        # Filter out already rated and save
        final_candidates = list(candidate_ids - exclude_ids)
        
        output = {
            "candidates": final_candidates,
            "count": len(final_candidates),
            "min_rating_threshold": MIN_RATING_FOR_SIMILAR,
            "similar_per_film": SIMILAR_MOVIES_PER_FILM,
        }
        
        with open(CANDIDATE_POOL_PATH, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Saved {len(final_candidates)} candidates to {CANDIDATE_POOL_PATH}")

    def run(self):
        """Main pipeline execution."""
        print("=" * 70)
        print("Pipeline 04a: Build Candidate Pool")
        print("=" * 70)
        
        self.db.connect()
        
        try:
            # Step 1: Get user interactions
            print("\n📖 Loading user interactions...")
            interactions, seen_ids, watchlist_ids = self.get_user_interactions()
            print(f"  Found {len(seen_ids)} seen films, {len(watchlist_ids)} in watchlist")
            
            # Step 2: Get highly rated films (seeds)
            highly_rated = get_highly_rated_movies(interactions, MIN_RATING_FOR_SIMILAR)
            self.stats["highly_rated"] = len(highly_rated)
            print(f"  Found {len(highly_rated)} films rated >= {MIN_RATING_FOR_SIMILAR}")
            
            # Step 3: Expand via TMDb Similar
            candidate_ids = self.expand_candidate_pool(highly_rated)
            
            # Step 4: Explicitly Add Watchlist!
            print(f"  Adding {len(watchlist_ids)} movies from watchlist to candidate pool")
            candidate_ids.update(watchlist_ids)
            self.stats["unique_candidates"] = len(candidate_ids)
            
            # Step 5: Ensure features exist for all candidates (excluding seen)
            self.ensure_movie_features(candidate_ids, seen_ids)
            
            # Step 6: Save candidate pool
            self.save_candidate_pool(candidate_ids, seen_ids)
            
            # Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Seed films (rated >= {MIN_RATING_FOR_SIMILAR}): {self.stats['highly_rated']}")
            print(f"Similar movies fetched:    {self.stats['similar_fetched']}")
            print(f"Unique candidates:         {self.stats['unique_candidates']}")
            print(f"New movies processed:      {self.stats['new_movies_processed']}")
            print(f"📡 TMDB API calls:         {self.stats['api_calls']}")
            print("=" * 70)
            
        finally:
            self.db.close()


if __name__ == "__main__":
    CandidatePoolBuilder().run()
