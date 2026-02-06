#!/usr/bin/env python3
"""
Pipeline 05: Build Emotion Vectors (Plutchik V2)

Computes emotion distributions for all movies using Plutchik's wheel:
- 8 primary emotions via softmax of cosine similarities to anchors
- 8 dyads (combinations of adjacent primaries)
- Confidence score for each film

Output: data/emotions/movie_emotions.parquet
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import EMBEDDING_MODEL, EMBEDDINGS_DIR
from config.emotions import (
    PRIMARY_EMOTIONS, 
    PRIMARY_ORDER, 
    DYADS,
    EMOTION_TEMPERATURE,
    get_anchor_texts,
)
from embeddings.encoder import MovieEncoder


# Output paths
EMOTIONS_DIR = Path(__file__).parent.parent / "data" / "emotions"


class EmotionVectorBuilder:
    """Builds emotion vectors for all movies with embeddings."""
    
    def __init__(self, temperature: float = EMOTION_TEMPERATURE):
        """
        Initialize builder.
        
        Args:
            temperature: τ for softmax (lower = more contrasty)
        """
        self.encoder = MovieEncoder(EMBEDDING_MODEL)
        self.temperature = temperature
        
        # Will be loaded
        self.movie_embeddings = None
        self.tmdb_to_index = None
        self.anchor_embeddings = None
        
        # Statistics
        self.stats = {
            "movies_processed": 0,
            "avg_confidence": 0.0,
            "avg_entropy": 0.0,
        }
    
    def load_movie_embeddings(self) -> tuple[np.ndarray, dict]:
        """Load existing movie embeddings from disk."""
        embeddings_path = Path(EMBEDDINGS_DIR) / "movie_embeddings.npy"
        index_path = Path(EMBEDDINGS_DIR) / "tmdb_to_index.json"
        
        if not embeddings_path.exists():
            raise FileNotFoundError(f"Embeddings not found: {embeddings_path}")
        
        embeddings = np.load(embeddings_path)
        
        with open(index_path, "r") as f:
            tmdb_to_index = json.load(f)
        
        # Convert string keys to int
        tmdb_to_index = {int(k): v for k, v in tmdb_to_index.items()}
        
        print(f"✓ Loaded {embeddings.shape[0]} movie embeddings ({embeddings.shape[1]} dims)")
        return embeddings, tmdb_to_index
    
    def encode_anchors(self) -> np.ndarray:
        """
        Encode emotion anchors into embeddings.
        
        Returns:
            Anchor matrix A ∈ R^(8×D)
        """
        print(f"\nEncoding {len(PRIMARY_ORDER)} emotion anchors...")
        
        anchor_texts = get_anchor_texts()
        # Sort by PRIMARY_ORDER for consistent indexing
        anchor_dict = dict(anchor_texts)
        ordered_texts = [anchor_dict[emo] for emo in PRIMARY_ORDER]
        
        embeddings = self.encoder.encode(ordered_texts, show_progress=False)
        
        print(f"✓ Encoded {len(PRIMARY_ORDER)} anchors")
        return embeddings
    
    def compute_emotion_vector(self, movie_embedding: np.ndarray) -> np.ndarray:
        """
        Compute emotion distribution for a single movie.
        
        E_film = softmax(cosine(v, A) / τ)
        
        Args:
            movie_embedding: Movie embedding vector (D,)
            
        Returns:
            Emotion distribution (8,) summing to 1.0
        """
        # Cosine similarity to each anchor
        # Reshape for sklearn: (1, D) vs (8, D)
        cosines = sklearn_cosine(
            movie_embedding.reshape(1, -1), 
            self.anchor_embeddings
        )[0]  # Shape: (8,)
        
        # Softmax with temperature
        logits = cosines / self.temperature
        exp_logits = np.exp(logits - np.max(logits))  # Numerical stability
        probs = exp_logits / np.sum(exp_logits)
        
        return probs.astype(np.float32)
    
    def compute_dyads(self, E_film: np.ndarray) -> dict:
        """
        Compute dyad scores from primary emotion distribution.
        
        D_dyad = sqrt(E_p1 × E_p2) (geometric mean)
        
        Args:
            E_film: Primary emotion distribution (8,)
            
        Returns:
            Dictionary of dyad scores
        """
        dyad_scores = {}
        
        for dyad_name, (p1, p2) in DYADS.items():
            idx1 = PRIMARY_ORDER.index(p1)
            idx2 = PRIMARY_ORDER.index(p2)
            
            # Geometric mean
            score = np.sqrt(E_film[idx1] * E_film[idx2])
            dyad_scores[f"d_{dyad_name}"] = float(score)
        
        return dyad_scores
    
    def compute_confidence(self, E_film: np.ndarray) -> float:
        """
        Compute confidence score (how "typed" the film is).
        
        conf = top1 - top2
        
        Args:
            E_film: Primary emotion distribution (8,)
            
        Returns:
            Confidence score [0, 1]
        """
        sorted_probs = np.sort(E_film)[::-1]
        return float(sorted_probs[0] - sorted_probs[1])
    
    def compute_entropy(self, E_film: np.ndarray) -> float:
        """Compute entropy of distribution (for diagnostics)."""
        E_film = np.clip(E_film, 1e-10, 1.0)  # Avoid log(0)
        return float(-np.sum(E_film * np.log(E_film)))
    
    def build_all_vectors(self) -> pd.DataFrame:
        """
        Build emotion vectors for all movies.
        
        Returns:
            DataFrame with columns:
            - tmdb_id
            - e_joy, e_trust, e_fear, e_surprise, e_sadness, e_disgust, e_anger, e_anticipation
            - d_ecstasy, d_admiration, d_terror, d_amazement, d_grief, d_loathing, d_rage, d_vigilance
            - confidence
            - entropy
        """
        print(f"\n🧮 Computing emotion vectors (τ={self.temperature})...")
        
        records = []
        confidences = []
        entropies = []
        
        tmdb_ids = list(self.tmdb_to_index.keys())
        total = len(tmdb_ids)
        
        for i, tmdb_id in enumerate(tmdb_ids):
            idx = self.tmdb_to_index[tmdb_id]
            movie_emb = self.movie_embeddings[idx]
            
            # Primary emotions
            E_film = self.compute_emotion_vector(movie_emb)
            
            # Dyads
            dyads = self.compute_dyads(E_film)
            
            # Confidence & entropy
            conf = self.compute_confidence(E_film)
            ent = self.compute_entropy(E_film)
            
            confidences.append(conf)
            entropies.append(ent)
            
            # Build record
            record = {"tmdb_id": tmdb_id}
            for j, emo in enumerate(PRIMARY_ORDER):
                record[f"e_{emo}"] = float(E_film[j])
            record.update(dyads)
            record["confidence"] = conf
            record["entropy"] = ent
            
            records.append(record)
            
            if (i + 1) % 500 == 0:
                print(f"  [{i+1}/{total}] Processed...")
        
        df = pd.DataFrame(records)
        
        # Stats
        self.stats["movies_processed"] = len(df)
        self.stats["avg_confidence"] = np.mean(confidences)
        self.stats["avg_entropy"] = np.mean(entropies)
        
        return df
    
    def save_vectors(self, df: pd.DataFrame) -> Path:
        """Save emotion vectors to parquet."""
        EMOTIONS_DIR.mkdir(parents=True, exist_ok=True)
        
        output_path = EMOTIONS_DIR / "movie_emotions.parquet"
        df.to_parquet(output_path, index=False)
        
        # Also save metadata
        metadata = {
            "created_at": datetime.now().isoformat(),
            "temperature": self.temperature,
            "movies_count": len(df),
            "avg_confidence": self.stats["avg_confidence"],
            "avg_entropy": self.stats["avg_entropy"],
            "primary_emotions": PRIMARY_ORDER,
            "dyads": list(DYADS.keys()),
        }
        
        meta_path = EMOTIONS_DIR / "emotion_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return output_path
    
    def run(self):
        """Execute the full pipeline."""
        print("=" * 70)
        print("Pipeline 05: Build Emotion Vectors (Plutchik)")
        print("=" * 70)
        
        # Load movie embeddings
        self.movie_embeddings, self.tmdb_to_index = self.load_movie_embeddings()
        
        # Encode anchors
        self.anchor_embeddings = self.encode_anchors()
        
        # Build emotion vectors
        df = self.build_all_vectors()
        
        # Save
        output_path = self.save_vectors(df)
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Movies processed:    {self.stats['movies_processed']}")
        print(f"Avg confidence:      {self.stats['avg_confidence']:.4f}")
        print(f"Avg entropy:         {self.stats['avg_entropy']:.4f}")
        print(f"Temperature (τ):     {self.temperature}")
        print(f"Output:              {output_path}")
        print("=" * 70)
        
        # Show sample films
        print("\n🎬 Sample emotion profiles:")
        self._show_sample_profiles(df)
        
        return df
    
    def _show_sample_profiles(self, df: pd.DataFrame, n: int = 5):
        """Show emotion profiles for sample films."""
        try:
            from clients.db import DatabaseClient
            db = DatabaseClient()
        except Exception:
            db = None
        
        # Get films with highest confidence
        top_confident = df.nlargest(n, "confidence")
        
        for _, row in top_confident.iterrows():
            tmdb_id = int(row["tmdb_id"])
            title = f"ID:{tmdb_id}"
            
            if db:
                try:
                    movie = db.get_movie_by_tmdb_id(tmdb_id)
                    if movie:
                        title = movie.get("title", title)
                except Exception:
                    pass
            
            # Find dominant emotion
            emo_cols = [c for c in df.columns if c.startswith("e_")]
            dominant = max(emo_cols, key=lambda c: row[c])
            dominant_score = row[dominant]
            
            print(f"  {title}: {dominant[2:]} ({dominant_score:.2%}) [conf: {row['confidence']:.2f}]")


def main():
    """Main entry point."""
    builder = EmotionVectorBuilder()
    builder.run()


if __name__ == "__main__":
    main()
