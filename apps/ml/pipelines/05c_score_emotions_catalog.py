#!/usr/bin/env python3
"""
Pipeline 05c: Score Emotions Catalog

Applies the trained emotion model to score all movies in the catalog.

Output format (aligned with spec):
- tmdb_id
- p_joie, p_confiance, p_peur, p_surprise, p_tristesse, p_degout, p_colere, p_anticipation
- top_emotion
- second_emotion  
- confidence (= p_top1 - p_top2)
- d_* dyads (optional)

Output:
- data/emotions/movie_emotions.parquet
"""
import sys
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import EMOTIONS_DATA_DIR, MODELS_DIR, EMBEDDINGS_DIR
from config.emotions import PRIMARY_ORDER, DYADS
from clients.db import DatabaseClient
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine


# French column names for probability outputs (per spec)
PROB_COLUMNS = {
    "joy": "p_joie",
    "trust": "p_confiance", 
    "fear": "p_peur",
    "surprise": "p_surprise",
    "sadness": "p_tristesse",
    "disgust": "p_degout",
    "anger": "p_colere",
    "anticipation": "p_anticipation",
}

# French dyad column names
DYAD_COLUMNS = {
    "ecstasy": "d_extase",
    "admiration": "d_admiration",
    "terror": "d_terreur",
    "amazement": "d_etonnement",
    "grief": "d_chagrin",
    "loathing": "d_aversion",
    "rage": "d_rage",
    "vigilance": "d_vigilance",
}


class EmotionCatalogScorer:
    """Scores all movies in catalog with trained emotion model."""
    
    def __init__(self, model_version: Optional[str] = None):
        """
        Initialize scorer.
        
        Args:
            model_version: Specific model version to use, or None for latest
        """
        self.db = DatabaseClient()
        self.model_version = model_version
        
        # Will be loaded
        self.model = None
        self.model_schema = None
        self.feature_schema = None
        self.movie_embeddings = None
        self.tmdb_to_index = None
        self.anchor_embeddings = None
        self.anchor_stats = None
        
        # Statistics
        self.stats = {
            "movies_scored": 0,
            "movies_skipped": 0,
            "avg_confidence": 0.0,
        }
    
    def _find_latest_model(self) -> str:
        """Find the latest emotion model version."""
        models_dir = Path(MODELS_DIR)
        model_files = list(models_dir.glob("emotion_v*.pkl"))
        
        if not model_files:
            raise FileNotFoundError("No emotion models found in models/")
        
        # Sort by timestamp in filename
        latest = sorted(model_files)[-1]
        version = latest.stem  # e.g., "emotion_v20260209_163000"
        
        print(f"✓ Found latest model: {version}")
        return version
    
    def _load_model(self) -> None:
        """Load trained model and schemas."""
        if self.model_version is None:
            self.model_version = self._find_latest_model()
        
        # Load model
        model_path = Path(MODELS_DIR) / f"{self.model_version}.pkl"
        with open(model_path, "rb") as f:
            self.model = pickle.load(f)
        print(f"✓ Loaded model from {model_path}")
        
        # Load model schema
        schema_path = Path(MODELS_DIR) / f"{self.model_version}_schema.json"
        with open(schema_path, "r") as f:
            self.model_schema = json.load(f)
        print(f"✓ Loaded model schema: {len(self.model_schema['feature_names'])} features")
    
    def _load_feature_resources(self) -> None:
        """Load embeddings, anchors, and feature schema."""
        # Movie embeddings
        embeddings_path = Path(EMBEDDINGS_DIR) / "movie_embeddings.npy"
        index_path = Path(EMBEDDINGS_DIR) / "tmdb_to_index.json"
        
        self.movie_embeddings = np.load(embeddings_path)
        with open(index_path, "r") as f:
            self.tmdb_to_index = {int(k): v for k, v in json.load(f).items()}
        print(f"✓ Loaded {len(self.tmdb_to_index)} movie embeddings")
        
        # Anchor embeddings
        anchor_path = Path(EMOTIONS_DATA_DIR) / "anchor_embeddings.npy"
        self.anchor_embeddings = np.load(anchor_path)
        print(f"✓ Loaded {self.anchor_embeddings.shape[0]} anchor embeddings")
        
        # Anchor stats (for z-scoring)
        stats_path = Path(EMOTIONS_DATA_DIR) / "anchor_stats.json"
        with open(stats_path, "r") as f:
            self.anchor_stats = json.load(f)
        print(f"✓ Loaded anchor z-score statistics")
        
        # Feature schema (vocabs)
        schema_path = Path(EMOTIONS_DATA_DIR) / "feature_schema.json"
        with open(schema_path, "r") as f:
            self.feature_schema = json.load(f)
        print(f"✓ Loaded feature schema")
    
    def _compute_anchor_logits(self, movie_embedding: np.ndarray) -> np.ndarray:
        """Compute raw cosine similarity to each emotion anchor."""
        cosines = sklearn_cosine(
            movie_embedding.reshape(1, -1),
            self.anchor_embeddings
        )[0]
        return cosines.astype(np.float32)
    
    def _z_score_logits(self, logits: np.ndarray) -> np.ndarray:
        """Apply z-score normalization to anchor logits."""
        result = np.zeros_like(logits)
        for i, emo in enumerate(PRIMARY_ORDER):
            mean = self.anchor_stats[emo]["mean"]
            std = self.anchor_stats[emo]["std"]
            if std > 1e-6:
                result[i] = (logits[i] - mean) / std
            else:
                result[i] = logits[i] - mean
        return result
    
    def _encode_multi_hot(self, values: List[str], vocab: List[str]) -> np.ndarray:
        """Encode values as multi-hot vector."""
        result = np.zeros(len(vocab), dtype=np.float32)
        for v in values:
            if v in vocab:
                result[vocab.index(v)] = 1.0
        return result
    
    def _build_features(self, tmdb_id: int, movie_features: dict) -> Optional[np.ndarray]:
        """Build feature vector for a single movie."""
        features = []
        
        # 1. Anchor logits (z-scored)
        if tmdb_id not in self.tmdb_to_index:
            return None
        
        movie_emb = self.movie_embeddings[self.tmdb_to_index[tmdb_id]]
        raw_logits = self._compute_anchor_logits(movie_emb)
        z_logits = self._z_score_logits(raw_logits)
        features.extend(z_logits)
        
        # 2. Genres multi-hot
        genre_vocab = self.feature_schema["genre_vocab"]
        raw_genres = movie_features.get("genres") or []
        if isinstance(raw_genres, str):
            raw_genres = json.loads(raw_genres)
        genre_names = [g.get("name") if isinstance(g, dict) else g for g in raw_genres]
        genre_names = [g for g in genre_names if g]
        genres_encoded = self._encode_multi_hot(genre_names, genre_vocab)
        features.extend(genres_encoded)
        
        # 3. Keywords multi-hot
        keyword_vocab = self.feature_schema["keyword_vocab"]
        raw_keywords = movie_features.get("keywords") or []
        if isinstance(raw_keywords, str):
            raw_keywords = json.loads(raw_keywords)
        keyword_names = [k.get("name") if isinstance(k, dict) else k for k in raw_keywords]
        keyword_names = [k for k in keyword_names if k]
        keywords_encoded = self._encode_multi_hot(keyword_names, keyword_vocab)
        features.extend(keywords_encoded)
        
        return np.array(features, dtype=np.float32)
    
    def _compute_dyads(self, probs: np.ndarray) -> Dict[str, float]:
        """Compute dyad scores from probability distribution."""
        dyad_scores = {}
        
        for dyad_name, (p1, p2) in DYADS.items():
            idx1 = PRIMARY_ORDER.index(p1)
            idx2 = PRIMARY_ORDER.index(p2)
            
            # Geometric mean
            score = np.sqrt(probs[idx1] * probs[idx2])
            col_name = DYAD_COLUMNS[dyad_name]
            dyad_scores[col_name] = float(score)
        
        return dyad_scores
    
    def _score_movie(self, tmdb_id: int, movie_features: dict) -> Optional[Dict]:
        """
        Score a single movie.
        
        Returns:
            Dict with probabilities, top emotions, confidence, dyads
        """
        features = self._build_features(tmdb_id, movie_features)
        if features is None:
            return None
        
        # Get probabilities
        probs = self.model.predict_proba(features.reshape(1, -1))[0]
        
        # Build result
        result = {"tmdb_id": tmdb_id}
        
        # Probability columns (French names per spec)
        for i, emo in enumerate(PRIMARY_ORDER):
            col_name = PROB_COLUMNS[emo]
            result[col_name] = float(probs[i])
        
        # Top emotions
        sorted_indices = np.argsort(probs)[::-1]
        result["top_emotion"] = PRIMARY_ORDER[sorted_indices[0]]
        result["second_emotion"] = PRIMARY_ORDER[sorted_indices[1]]
        
        # Confidence
        result["confidence"] = float(probs[sorted_indices[0]] - probs[sorted_indices[1]])
        
        # Dyads
        dyads = self._compute_dyads(probs)
        result.update(dyads)
        
        return result
    
    def run(self):
        """Execute the full scoring pipeline."""
        print("=" * 70)
        print("Pipeline 05c: Score Emotions Catalog")
        print("=" * 70)
        
        # Load model and resources
        self._load_model()
        self._load_feature_resources()
        
        self.db.connect()
        
        try:
            # Load all movie features
            print("\n📊 Loading movie features...")
            all_features = self.db.fetch_all("SELECT * FROM movie_features")
            features_by_tmdb = {f["tmdb_id"]: f for f in all_features}
            print(f"  Found {len(all_features)} movies with features")
            
            # Score all movies with embeddings
            print("\n🧮 Scoring catalog...")
            records = []
            confidences = []
            
            total = len(self.tmdb_to_index)
            for i, tmdb_id in enumerate(self.tmdb_to_index.keys()):
                # Get features
                movie_feats = features_by_tmdb.get(tmdb_id)
                if movie_feats is None:
                    self.stats["movies_skipped"] += 1
                    continue
                
                result = self._score_movie(tmdb_id, movie_feats)
                if result is None:
                    self.stats["movies_skipped"] += 1
                    continue
                
                records.append(result)
                confidences.append(result["confidence"])
                self.stats["movies_scored"] += 1
                
                if (i + 1) % 500 == 0:
                    print(f"  [{i+1}/{total}] Processed...")
            
            # Create DataFrame
            df = pd.DataFrame(records)
            
            # Ensure column order
            prob_cols = [PROB_COLUMNS[emo] for emo in PRIMARY_ORDER]
            dyad_cols = [DYAD_COLUMNS[d] for d in DYADS.keys()]
            ordered_cols = (
                ["tmdb_id"] 
                + prob_cols 
                + ["top_emotion", "second_emotion", "confidence"]
                + dyad_cols
            )
            df = df[ordered_cols]
            
            # Stats
            self.stats["avg_confidence"] = float(np.mean(confidences))
            
            # Save
            output_path = Path(EMOTIONS_DATA_DIR) / "movie_emotions.parquet"
            df.to_parquet(output_path, index=False)
            print(f"\n💾 Saved to {output_path}")
            
            # Save metadata
            metadata = {
                "created_at": datetime.now().isoformat(),
                "model_version": self.model_version,
                "movies_scored": self.stats["movies_scored"],
                "movies_skipped": self.stats["movies_skipped"],
                "avg_confidence": self.stats["avg_confidence"],
                "probability_columns": prob_cols,
                "dyad_columns": dyad_cols,
                "class_labels": PRIMARY_ORDER,
            }
            
            meta_path = Path(EMOTIONS_DATA_DIR) / "emotion_metadata.json"
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2)
            print(f"💾 Saved metadata to {meta_path}")
            
            # Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Model version:       {self.model_version}")
            print(f"Movies scored:       {self.stats['movies_scored']}")
            print(f"Movies skipped:      {self.stats['movies_skipped']}")
            print(f"Avg confidence:      {self.stats['avg_confidence']:.4f}")
            print(f"Output:              {output_path}")
            
            # Top emotion distribution
            print("\n🎬 Top emotion distribution:")
            emotion_counts = df["top_emotion"].value_counts()
            for emo, count in emotion_counts.items():
                pct = 100 * count / len(df)
                print(f"  {emo:15} {count:5d} ({pct:5.1f}%)")
            
            # Sanity check: show top 5 per emotion
            print("\n🔍 Top 5 movies per emotion (by probability):")
            self._show_top_per_emotion(df)
            
            print("=" * 70)
            
        finally:
            self.db.close()
    
    def _show_top_per_emotion(self, df: pd.DataFrame, n: int = 5) -> None:
        """Show top N movies per emotion for sanity check."""
        # Get movie titles
        self.db.connect()
        
        for emo in PRIMARY_ORDER[:4]:  # Show first 4 for brevity
            prob_col = PROB_COLUMNS[emo]
            top_df = df.nlargest(n, prob_col)
            
            print(f"\n  {emo.upper()}:")
            for _, row in top_df.iterrows():
                tmdb_id = int(row["tmdb_id"])
                prob = row[prob_col]
                
                movie = self.db.get_movie_by_tmdb_id(tmdb_id)
                title = movie.get("title", f"ID:{tmdb_id}") if movie else f"ID:{tmdb_id}"
                
                print(f"    {title[:35]:35} {prob:.3f}")


def main():
    """Main entry point."""
    scorer = EmotionCatalogScorer()
    scorer.run()


if __name__ == "__main__":
    main()
