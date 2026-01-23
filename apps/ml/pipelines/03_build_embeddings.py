#!/usr/bin/env python3
"""
Pipeline 03: Build Embeddings

Generates semantic embeddings for all movies using Sentence-Transformers
and saves them as numpy arrays with index mappings.
"""
import sys
import json
from pathlib import Path
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE, EMBEDDINGS_DIR
from clients.db import DatabaseClient
from embeddings.encoder import MovieEncoder


class EmbeddingBuilder:
    """Builds and saves movie embeddings."""
    
    def __init__(self, model_name: str = None):
        """
        Initialize builder.
        
        Args:
            model_name: Sentence-Transformers model name (default from config)
        """
        self.model_name = model_name or EMBEDDING_MODEL
        self.encoder = MovieEncoder(self.model_name)
        self.db = DatabaseClient()
        
        # Statistics
        self.stats = {
            "total": 0,
            "embedded": 0,
            "skipped": 0,
        }
    
    def fetch_movie_texts(self):
        """
        Fetch all movies with their text_for_embedding.
        
        Returns:
            List of (tmdb_id, text) tuples
        """
        query = """
            SELECT mf.tmdb_id, mf.text_for_embedding, m.title
            FROM movie_features mf
            JOIN movies m ON mf.tmdb_id = m.tmdb_id
            WHERE mf.text_for_embedding IS NOT NULL
            ORDER BY mf.tmdb_id
        """
        
        rows = self.db.fetch_all(query)
        
        movie_data = []
        for row in rows:
            if row['text_for_embedding']:
                movie_data.append({
                    'tmdb_id': row['tmdb_id'],
                    'title': row['title'],
                    'text': row['text_for_embedding']
                })
                self.stats["total"] += 1
            else:
                self.stats["skipped"] += 1
        
        return movie_data
    
    def build_embeddings(self, movie_data):
        """
        Generate embeddings for all movies.
        
        Args:
            movie_data: List of movie dictionaries with tmdb_id, title, text
            
        Returns:
            Tuple of (embeddings_array, tmdb_ids_list)
        """
        print(f"\nGenerating embeddings for {len(movie_data)} movies...")
        print(f"Model: {self.model_name}")
        print(f"Batch size: {EMBEDDING_BATCH_SIZE}")
        
        # Extract texts and IDs
        texts = [m['text'] for m in movie_data]
        tmdb_ids = [m['tmdb_id'] for m in movie_data]
        
        # Generate embeddings
        embeddings = self.encoder.encode(
            texts,
            batch_size=EMBEDDING_BATCH_SIZE,
            show_progress=True
        )
        
        print(f"✓ Generated embeddings with shape: {embeddings.shape}")
        
        return embeddings, tmdb_ids
    
    def save_artifacts(self, embeddings: np.ndarray, tmdb_ids: list, movie_data: list):
        """
        Save embeddings and metadata to disk.
        
        Args:
            embeddings: Numpy array of embeddings
            tmdb_ids: List of TMDB IDs
            movie_data: List of movie dictionaries
        """
        # Ensure directory exists
        Path(EMBEDDINGS_DIR).mkdir(parents=True, exist_ok=True)
        
        # Save embeddings as .npy
        embeddings_path = Path(EMBEDDINGS_DIR) / "movie_embeddings.npy"
        np.save(embeddings_path, embeddings)
        print(f"✓ Saved embeddings: {embeddings_path}")
        
        # Save TMDB ID index
        index_path = Path(EMBEDDINGS_DIR) / "tmdb_id_index.json"
        with open(index_path, "w") as f:
            json.dump(tmdb_ids, f, indent=2)
        print(f"✓ Saved ID index: {index_path}")
        
        # Save metadata
        metadata = {
            "model_name": self.model_name,
            "embedding_dimension": int(embeddings.shape[1]),
            "num_movies": int(embeddings.shape[0]),
            "created_at": "now",
            "movies": [
                {
                    "tmdb_id": m['tmdb_id'],
                    "title": m['title'],
                    "index": i
                }
                for i, m in enumerate(movie_data)
            ]
        }
        
        metadata_path = Path(EMBEDDINGS_DIR) / "embedding_meta.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"✓ Saved metadata: {metadata_path}")
        
        # Save mapping for quick lookups
        tmdb_to_index = {tmdb_id: i for i, tmdb_id in enumerate(tmdb_ids)}
        mapping_path = Path(EMBEDDINGS_DIR) / "tmdb_to_index.json"
        with open(mapping_path, "w") as f:
            json.dump(tmdb_to_index, f, indent=2)
        print(f"✓ Saved mapping: {mapping_path}")
    
    def run(self):
        """Main embedding generation process."""
        print("=" * 60)
        print("Pipeline 03: Build Embeddings")
        print("=" * 60)
        
        # Connect to database
        self.db.connect()
        
        # Fetch movie data
        print("\nFetching movie texts from database...")
        movie_data = self.fetch_movie_texts()
        
        if not movie_data:
            print("✗ No movies found with text_for_embedding!")
            self.db.close()
            return
        
        print(f"✓ Found {len(movie_data)} movies with text")
        
        # Build embeddings
        embeddings, tmdb_ids = self.build_embeddings(movie_data)
        self.stats["embedded"] = len(tmdb_ids)
        
        # Save artifacts
        print(f"\nSaving artifacts to {EMBEDDINGS_DIR}...")
        self.save_artifacts(embeddings, tmdb_ids, movie_data)
        
        # Close database
        self.db.close()
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total movies:      {self.stats['total']}")
        print(f"✓ Embedded:        {self.stats['embedded']}")
        print(f"⊘ Skipped (no text): {self.stats['skipped']}")
        print(f"Embedding dim:     {embeddings.shape[1]}")
        print(f"Model:             {self.model_name}")
        print("=" * 60)


if __name__ == "__main__":
    # Allow custom model via CLI
    model_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    builder = EmbeddingBuilder(model_name=model_name)
    builder.run()
