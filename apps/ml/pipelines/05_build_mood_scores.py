#!/usr/bin/env python3
"""
Pipeline 05: Build Mood Scores

Calculates similarity scores between mood embeddings and all taste candidates.
Pre-computes scores for efficient filtering in the web app.
"""
import sys
import json
from pathlib import Path
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import EMBEDDING_MODEL, EMBEDDINGS_DIR
from config.moods import MOODS, get_all_mood_texts
from clients.db import DatabaseClient
from embeddings.encoder import MovieEncoder


class MoodScoreBuilder:
    """Builds mood similarity scores for all taste candidates."""
    
    def __init__(self):
        """Initialize builder."""
        self.encoder = MovieEncoder(EMBEDDING_MODEL)
        self.db = DatabaseClient()
        
        # Statistics
        self.stats = {
            "moods_encoded": 0,
            "candidates_processed": 0,
            "scores_generated": 0,
        }
    
    def load_movie_embeddings(self) -> tuple[np.ndarray, dict]:
        """
        Load existing movie embeddings from disk.
        
        Returns:
            Tuple of (embeddings_array, tmdb_to_index_mapping)
        """
        embeddings_path = Path(EMBEDDINGS_DIR) / "movie_embeddings.npy"
        index_path = Path(EMBEDDINGS_DIR) / "tmdb_to_index.json"
        
        if not embeddings_path.exists():
            raise FileNotFoundError(f"Embeddings not found: {embeddings_path}")
        
        embeddings = np.load(embeddings_path)
        
        with open(index_path, "r") as f:
            tmdb_to_index = json.load(f)
        
        # Convert string keys to int (JSON serializes dict keys as strings)
        tmdb_to_index = {int(k): v for k, v in tmdb_to_index.items()}
        
        print(f"✓ Loaded {embeddings.shape[0]} movie embeddings")
        return embeddings, tmdb_to_index
    
    def encode_moods(self) -> dict[str, np.ndarray]:
        """
        Encode all moods into embeddings.
        
        Returns:
            Dictionary mapping mood_id to embedding vector
        """
        print(f"\nEncoding {len(MOODS)} moods...")
        
        mood_texts = get_all_mood_texts()
        mood_ids = [m[0] for m in mood_texts]
        texts = [m[1] for m in mood_texts]
        
        embeddings = self.encoder.encode(texts, show_progress=False)
        
        mood_embeddings = {}
        for i, mood_id in enumerate(mood_ids):
            mood_embeddings[mood_id] = embeddings[i]
        
        self.stats["moods_encoded"] = len(mood_embeddings)
        print(f"✓ Encoded {len(mood_embeddings)} moods")
        
        return mood_embeddings
    
    def get_taste_candidate_tmdb_ids(self) -> list[int]:
        """Get all TMDB IDs from taste_candidates table."""
        rows = self.db.fetch_all("SELECT tmdb_id FROM taste_candidates")
        return [row["tmdb_id"] for row in rows]
    
    def calculate_scores(
        self, 
        mood_embeddings: dict[str, np.ndarray],
        movie_embeddings: np.ndarray,
        tmdb_to_index: dict[int, int],
        candidate_ids: list[int]
    ) -> list[tuple[int, str, float]]:
        """
        Calculate similarity scores between all moods and candidates.
        
        Args:
            mood_embeddings: Dict of mood_id -> embedding
            movie_embeddings: Matrix of movie embeddings
            tmdb_to_index: Mapping of tmdb_id -> embedding index
            candidate_ids: List of TMDB IDs to score
            
        Returns:
            List of (tmdb_id, mood_id, score) tuples
        """
        print(f"\nCalculating scores for {len(candidate_ids)} candidates × {len(mood_embeddings)} moods...")
        
        scores = []
        
        # Stack mood embeddings into matrix for batch computation
        mood_ids = list(mood_embeddings.keys())
        mood_matrix = np.stack([mood_embeddings[mid] for mid in mood_ids])
        
        processed = 0
        for tmdb_id in candidate_ids:
            if tmdb_id not in tmdb_to_index:
                # Movie doesn't have an embedding yet
                continue
            
            idx = tmdb_to_index[tmdb_id]
            movie_emb = movie_embeddings[idx].reshape(1, -1)
            
            # Calculate cosine similarity with all moods at once
            similarities = cosine_similarity(movie_emb, mood_matrix)[0]
            
            for i, mood_id in enumerate(mood_ids):
                score = float(similarities[i])
                scores.append((tmdb_id, mood_id, score))
            
            processed += 1
            if processed % 500 == 0:
                print(f"  Processed {processed}/{len(candidate_ids)} candidates...")
        
        self.stats["candidates_processed"] = processed
        self.stats["scores_generated"] = len(scores)
        
        print(f"✓ Generated {len(scores)} scores")
        return scores
    
    def save_moods_to_db(self, mood_embeddings: dict[str, np.ndarray]):
        """Save moods with their embeddings to database."""
        print("\nSaving moods to database...")
        
        for mood in MOODS:
            embedding = mood_embeddings[mood["id"]].tolist()
            self.db.upsert_mood(
                mood_id=mood["id"],
                name=mood["name"],
                description=mood["description"],
                embedding=embedding
            )
        
        print(f"✓ Saved {len(MOODS)} moods")
    
    def save_scores_to_db(self, scores: list[tuple[int, str, float]]):
        """Save all mood scores to database."""
        print(f"\nSaving {len(scores)} scores to database...")
        
        # Clear existing scores
        self.db.clear_movie_mood_scores()
        
        # Insert in batches
        batch_size = 1000
        for i in range(0, len(scores), batch_size):
            batch = scores[i:i + batch_size]
            self.db.insert_movie_mood_scores(batch)
            print(f"  Inserted {min(i + batch_size, len(scores))}/{len(scores)} scores...")
        
        print(f"✓ Saved all scores")
    
    def print_sample_results(self, scores: list[tuple[int, str, float]]):
        """Print sample results for verification."""
        print("\n" + "=" * 60)
        print("SAMPLE RESULTS (Top films per mood)")
        print("=" * 60)
        
        # Group by mood
        mood_scores: dict[str, list] = {}
        for tmdb_id, mood_id, score in scores:
            if mood_id not in mood_scores:
                mood_scores[mood_id] = []
            mood_scores[mood_id].append((tmdb_id, score))
        
        # Get movie titles for display
        movies = {row["tmdb_id"]: row["title"] for row in self.db.fetch_all(
            "SELECT tmdb_id, title FROM movies"
        )}
        
        # Show top 3 for first 5 moods
        for mood_id in list(mood_scores.keys())[:5]:
            mood_name = next((m["name"] for m in MOODS if m["id"] == mood_id), mood_id)
            print(f"\n🎭 {mood_name}:")
            
            top = sorted(mood_scores[mood_id], key=lambda x: x[1], reverse=True)[:3]
            for tmdb_id, score in top:
                title = movies.get(tmdb_id, f"TMDB:{tmdb_id}")
                print(f"   {score:.0%} - {title}")
    
    def run(self):
        """Main mood score generation process."""
        print("=" * 60)
        print("Pipeline 05: Build Mood Scores")
        print("=" * 60)
        
        # Connect to database
        self.db.connect()
        
        try:
            # Load movie embeddings
            print("\nLoading movie embeddings...")
            movie_embeddings, tmdb_to_index = self.load_movie_embeddings()
            
            # Encode moods
            mood_embeddings = self.encode_moods()
            
            # Get candidate IDs
            print("\nFetching taste candidates...")
            candidate_ids = self.get_taste_candidate_tmdb_ids()
            print(f"✓ Found {len(candidate_ids)} candidates")
            
            # Calculate scores
            scores = self.calculate_scores(
                mood_embeddings,
                movie_embeddings,
                tmdb_to_index,
                candidate_ids
            )
            
            # Save to database
            self.save_moods_to_db(mood_embeddings)
            self.save_scores_to_db(scores)
            
            # Print sample results
            self.print_sample_results(scores)
            
            # Print summary
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(f"Moods encoded:        {self.stats['moods_encoded']}")
            print(f"Candidates processed: {self.stats['candidates_processed']}")
            print(f"Scores generated:     {self.stats['scores_generated']}")
            print("=" * 60)
            
        finally:
            self.db.close()


if __name__ == "__main__":
    builder = MoodScoreBuilder()
    builder.run()
