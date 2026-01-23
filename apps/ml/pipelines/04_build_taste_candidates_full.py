#!/usr/bin/env python3
"""
Pipeline 04 (Full Version): Build Taste Candidates - End-to-End [OPTIMIZED]

Features:
1. Unified API calls: Fetch Details, Credits, and Keywords in 1 single call (append_to_response).
2. Resumable: Skips movies already in DB with features.
3. Enhanced retry logic for SSL/Network issues.
"""
import sys
import json
import time
from pathlib import Path
import numpy as np
from typing import Set, List, Dict, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    EMBEDDINGS_DIR,
    MIN_RATING_FOR_SIMILAR,
    SIMILAR_MOVIES_PER_FILM,
    MAX_TASTE_CANDIDATES,
    TMDB_RATE_LIMIT_DELAY,
    EMBEDDING_MODEL,
)
from clients.db import DatabaseClient
from clients.tmdb import (
    get_similar_movies,
    get_movie_details,
)
from features.preference_score import calculate_user_profile, get_highly_rated_movies
from features.text_builder import extract_movie_metadata, build_text_for_embedding
from embeddings.encoder import MovieEncoder
from embeddings.similarity import cosine_similarity_matrix


class FullTasteCandidateBuilder:
    """Builds personalized movie recommendations with optimized pipeline."""

    def __init__(self):
        """Initialize builder."""
        self.db = DatabaseClient()
        self.encoder = MovieEncoder(model_name=EMBEDDING_MODEL)

        # Load existing embeddings
        self.embeddings, self.tmdb_to_index, self.index_to_tmdb = self.load_embeddings()

        # Statistics
        self.stats = {
            "highly_rated": 0,
            "similar_fetched": 0,
            "unique_candidates": 0,
            "api_calls": 0,
            "new_movies_processed": 0,
            "total_candidates_scored": 0,
            "top_candidates_saved": 0,
        }

    def load_embeddings(self):
        """Load embeddings and index mappings."""
        embeddings_path = Path(EMBEDDINGS_DIR) / "movie_embeddings.npy"
        index_path = Path(EMBEDDINGS_DIR) / "tmdb_id_index.json"
        mapping_path = Path(EMBEDDINGS_DIR) / "tmdb_to_index.json"

        print(f"Loading existing embeddings from {EMBEDDINGS_DIR}...")
        embeddings = np.load(embeddings_path)
        with open(index_path, "r") as f:
            index_to_tmdb = json.load(f)
        with open(mapping_path, "r") as f:
            tmdb_to_index = {int(k): v for k, v in json.load(f).items()}
        print(f"✓ Loaded {embeddings.shape[0]} existing embeddings")
        return embeddings, tmdb_to_index, index_to_tmdb

    def get_user_interactions_summary(self):
        """Get rated and wishlisted IDs to exclude."""
        interactions = self.db.get_all_interactions()
        rated_ids = {i["tmdb_id"] for i in interactions if i.get("rating") is not None}
        all_interaction_ids = {i["tmdb_id"] for i in interactions}
        return interactions, rated_ids, all_interaction_ids

    def expand_candidate_pool(self, highly_rated_ids: list) -> set:
        """Fetch similar movies via TMDB."""
        candidates = set()
        print(f"\nExpanding candidate pool from {len(highly_rated_ids)} films...")
        
        for i, tmdb_id in enumerate(highly_rated_ids, 1):
            try:
                time.sleep(TMDB_RATE_LIMIT_DELAY)
                similar = get_similar_movies(tmdb_id, language="en-US", page=1)
                self.stats["api_calls"] += 1
                
                sim_ids = [m["id"] for m in similar.get("results", [])[:SIMILAR_MOVIES_PER_FILM]]
                candidates.update(sim_ids)
                self.stats["similar_fetched"] += len(sim_ids)
                
                if i % 5 == 0:
                    print(f"  Processed {i}/{len(highly_rated_ids)} films...")
            except Exception as e:
                print(f"  ✗ Error fetching similar for {tmdb_id}: {e}")
                
        print(f"✓ Found {len(candidates)} candidate TMDB IDs")
        return candidates

    def process_new_candidates(self, candidate_ids: set, exclude_ids: set) -> Dict[int, np.ndarray]:
        """
        Process candidates that are not in DB or don't have embeddings.
        Checked against DB to be fully resumable.
        """
        # 1. Skip movies already rated by user
        discovery_pool = candidate_ids - exclude_ids
        print(f"\nDiscovery pool: {len(discovery_pool)} movies (excluding your rated films)")

        # 2. Identify missing features
        print("Checking which movies need TMDB data...")
        existing_feats = {r['tmdb_id'] for r in self.db.fetch_all("SELECT tmdb_id FROM movie_features")}
        
        to_fetch = [tid for tid in discovery_pool if tid not in existing_feats and tid not in self.tmdb_to_index]
        
        if not to_fetch:
            print("✓ All candidates already have features in database.")
            return {}

        print(f"Fetching metadata for {len(to_fetch)} movies from TMDB (Rate: ~40/min)...")
        
        for i, tmdb_id in enumerate(to_fetch, 1):
            try:
                # Rate limit
                time.sleep(TMDB_RATE_LIMIT_DELAY)
                
                # Optimized call: All-in-one
                data = get_movie_details(tmdb_id, language="en-US", append_to_response="credits,keywords")
                self.stats["api_calls"] += 1
                
                # Basic info
                release_date = data.get("release_date", "")
                release_year = int(release_date[:4]) if release_date else None
                
                # Upsert handles duplicates automatically
                self.db.upsert_movie(
                    tmdb_id, 
                    data.get("title", "Unknown"), 
                    release_year, 
                    data.get("poster_path")
                )
                
                # Build metadata for features
                metadata = extract_movie_metadata(data, data.get("credits", {}), {"keywords": data.get("keywords", {}).get("keywords", [])})
                
                text = build_text_for_embedding(
                    overview=metadata["overview"],
                    genres=metadata["genres"],
                    keywords=metadata["keywords"],
                    cast=metadata["cast"],
                    director=metadata["director"],
                    lang="en"
                )
                
                # Upsert features
                self.db.upsert_movie_features(
                    tmdb_id=tmdb_id,
                    lang="en",
                    overview=metadata["overview"],
                    keywords=data.get("keywords", {}).get("keywords", []),
                    genres=data.get("genres", []),
                    cast=data.get("credits", {}).get("cast", [])[:10],
                    crew=metadata["crew"],
                    text_for_embedding=text
                )
                
                self.stats["new_movies_processed"] += 1
                if i % 5 == 0:
                    print(f"  [{i}/{len(to_fetch)}] {data.get('title')}... saved.")

            except Exception as e:
                print(f"  ✗ Error on ID {tmdb_id}: {e}")
                # Wait a bit longer if we hit an error (backoff)
                time.sleep(5)
                
        return {}

    def generate_missing_embeddings(self, candidate_ids: set, exclude_ids: set) -> Dict[int, np.ndarray]:
        """Generate embeddings for all candidates that don't have one in the matrix."""
        print("\nGenerating embeddings for missing candidates...")
        
        ids_to_encode = []
        texts_to_encode = []
        
        for tmdb_id in candidate_ids:
            if tmdb_id in exclude_ids: continue
            if tmdb_id in self.tmdb_to_index: continue
            
            # Fetch text from DB
            feat = self.db.fetch_one("SELECT text_for_embedding FROM movie_features WHERE tmdb_id = %s", (tmdb_id,))
            if feat and feat.get("text_for_embedding"):
                ids_to_encode.append(tmdb_id)
                texts_to_encode.append(feat["text_for_embedding"])
        
        if not ids_to_encode:
            print("✓ No missing embeddings to generate")
            return {}
            
        print(f"  Encoding {len(texts_to_encode)} movie texts...")
        embeddings = self.encoder.encode(texts_to_encode, batch_size=32, show_progress=True)
        
        new_map = {tid: emb for tid, emb in zip(ids_to_encode, embeddings)}
        print(f"✓ Generated {len(new_map)} new embeddings")
        return new_map

    def run(self):
        """Unified Pipeline 04 run."""
        print("=" * 70)
        print("Pipeline 04 [OPTIMIZED]: Personalized Recommendations")
        print("=" * 70)
        
        self.db.connect()
        
        # 1. Context
        interactions, rated_ids, all_ids = self.get_user_interactions_summary()
        user_profile = calculate_user_profile(interactions, self.embeddings, self.tmdb_to_index)
        
        # 2. Candidates
        highly_rated = get_highly_rated_movies(interactions, MIN_RATING_FOR_SIMILAR)
        self.stats["highly_rated"] = len(highly_rated)
        
        candidate_ids = self.expand_candidate_pool(highly_rated)
        
        # 3. Process new candidates (API phase)
        # We skip already rated movies to focus on discovery
        self.process_new_candidates(candidate_ids, rated_ids)
        
        # 4. Generate embeddings (ML phase)
        new_embeddings = self.generate_missing_embeddings(candidate_ids, rated_ids)
        
        # 5. Score
        print("\nScoring recommendations...")
        final_scores = []
        for tid in candidate_ids:
            if tid in rated_ids: continue
            
            emb = None
            if tid in self.tmdb_to_index:
                emb = self.embeddings[self.tmdb_to_index[tid]]
            elif tid in new_embeddings:
                emb = new_embeddings[tid]
                
            if emb is not None:
                score = cosine_similarity_matrix(user_profile, emb.reshape(1, -1))[0]
                final_scores.append((tid, float(score)))
                
        final_scores.sort(key=lambda x: x[1], reverse=True)
        self.stats["total_candidates_scored"] = len(final_scores)
        
        # 6. Save & Show
        top_n = final_scores[:MAX_TASTE_CANDIDATES]
        self.db.clear_taste_candidates()
        self.db.insert_taste_candidates(top_n, f"{EMBEDDING_MODEL}_v2")
        self.stats["top_candidates_saved"] = len(top_n)
        
        print(f"\n🎬 TOP 10 RECOMMENDATIONS:")
        for i, (tid, score) in enumerate(top_n[:10], 1):
            m = self.db.get_movie_by_tmdb_id(tid)
            print(f"  {i}. {m['title']} ({m.get('release_year', '?')}) - Score: {score:.3f}")

        # 7. Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Films rated HIGHLY:        {self.stats['highly_rated']}")
        print(f"Candidates FOUND:          {self.stats['unique_candidates']}")
        print(f"New movies FETCHED:        {self.stats['new_movies_processed']}")
        print(f"Candidates SCORÉD:         {self.stats['total_candidates_scored']}")
        print(f"📡 TMDB API calls:         {self.stats['api_calls']}")
        print("=" * 70)
        
        self.db.close()

if __name__ == "__main__":
    FullTasteCandidateBuilder().run()
