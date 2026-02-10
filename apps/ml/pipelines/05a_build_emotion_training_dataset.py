#!/usr/bin/env python3
"""
Pipeline 05a: Build Emotion Training Dataset

Constructs training data for supervised emotion classification from:
- movie_emotion_labels (ground truth labels)
- movie_embeddings (anchor logit features)
- movie_features (genres, keywords)

Features:
- anchor_logits_8: Z-scored cosine similarity to each emotion anchor
- genres: multi-hot encoding (top 20)
- keywords: multi-hot encoding (top 300)

Labels:
- 8-class classification (Plutchik primaries)

Output:
- data/emotions/train_X.parquet
- data/emotions/train_y.parquet  
- data/emotions/feature_schema.json
- data/emotions/anchor_embeddings.npy
- data/emotions/anchor_stats.json
"""
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    EMOTIONS_DATA_DIR,
    EMBEDDINGS_DIR,
    EMBEDDING_MODEL,
    TOP_GENRES,
    TOP_KEYWORDS_EMOTION,
)
from config.emotions import PRIMARY_ORDER, get_anchor_texts
from clients.db import DatabaseClient
from embeddings.encoder import MovieEncoder
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine


class EmotionTrainingDatasetBuilder:
    """Builds training dataset for supervised emotion classification."""
    
    def __init__(self):
        """Initialize builder."""
        self.db = DatabaseClient()
        self.encoder = MovieEncoder(EMBEDDING_MODEL)
        
        # Will be loaded/computed
        self.movie_embeddings = None
        self.tmdb_to_index = None
        self.anchor_embeddings = None
        self.anchor_stats = {}  # mean/std for z-score
        
        # Vocabularies
        self.genre_vocab = []
        self.keyword_vocab = []
        
        # Statistics
        self.stats = {
            "total_labels": 0,
            "labels_with_embeddings": 0,
            "labels_with_features": 0,
            "class_distribution": {},
        }
    
    def _load_movie_embeddings(self) -> Tuple[np.ndarray, Dict[int, int]]:
        """Load movie embeddings from disk."""
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
    
    def _encode_anchors(self) -> np.ndarray:
        """Encode emotion anchors into embeddings."""
        print(f"\n🎯 Encoding {len(PRIMARY_ORDER)} emotion anchors...")
        
        anchor_texts = get_anchor_texts()
        # Sort by PRIMARY_ORDER for consistent indexing
        anchor_dict = dict(anchor_texts)
        ordered_texts = [anchor_dict[emo] for emo in PRIMARY_ORDER]
        
        embeddings = self.encoder.encode(ordered_texts, show_progress=False)
        
        print(f"✓ Encoded {len(PRIMARY_ORDER)} anchors")
        return embeddings
    
    def _compute_anchor_logits(self, movie_embedding: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity to each emotion anchor.
        
        Args:
            movie_embedding: Single movie embedding (D,)
            
        Returns:
            Raw anchor logits (8,) - NOT z-scored
        """
        cosines = sklearn_cosine(
            movie_embedding.reshape(1, -1),
            self.anchor_embeddings
        )[0]  # Shape: (8,)
        
        return cosines.astype(np.float32)
    
    def _compute_anchor_stats(self, logits_matrix: np.ndarray) -> Dict[str, Dict[str, float]]:
        """
        Compute mean/std for z-score normalization.
        
        Args:
            logits_matrix: Matrix of anchor logits (N_samples x 8)
            
        Returns:
            Dict with mean/std per emotion
        """
        stats = {}
        for i, emo in enumerate(PRIMARY_ORDER):
            col = logits_matrix[:, i]
            stats[emo] = {
                "mean": float(np.mean(col)),
                "std": float(np.std(col)),
            }
        return stats
    
    def _z_score_logits(self, logits: np.ndarray) -> np.ndarray:
        """
        Apply z-score normalization to anchor logits.
        
        Args:
            logits: Raw anchor logits (8,)
            
        Returns:
            Z-scored logits (8,)
        """
        result = np.zeros_like(logits)
        for i, emo in enumerate(PRIMARY_ORDER):
            mean = self.anchor_stats[emo]["mean"]
            std = self.anchor_stats[emo]["std"]
            if std > 1e-6:
                result[i] = (logits[i] - mean) / std
            else:
                result[i] = logits[i] - mean
        return result
    
    def _build_vocabularies(self, movie_features: List[dict]) -> None:
        """Build vocabularies for genres and keywords."""
        print("\n📖 Building feature vocabularies...")
        
        genre_counter = Counter()
        keyword_counter = Counter()
        
        for feat in movie_features:
            if feat.get("genres"):
                genres = feat["genres"] if isinstance(feat["genres"], list) else json.loads(feat["genres"])
                for g in genres:
                    name = g.get("name") if isinstance(g, dict) else g
                    if name:
                        genre_counter[name] += 1
            
            if feat.get("keywords"):
                keywords = feat["keywords"] if isinstance(feat["keywords"], list) else json.loads(feat["keywords"])
                for k in keywords:
                    name = k.get("name") if isinstance(k, dict) else k
                    if name:
                        keyword_counter[name] += 1
        
        self.genre_vocab = [g for g, _ in genre_counter.most_common(TOP_GENRES)]
        # GridLab: KW100 best F1/stability trade-off (CV coeff 0.053 vs 0.080 for KW300)
        self.keyword_vocab = [k for k, _ in keyword_counter.most_common(TOP_KEYWORDS_EMOTION)]
        
        print(f"  Genres: {len(self.genre_vocab)}")
        print(f"  Keywords: {len(self.keyword_vocab)} (GridLab: TOP_KEYWORDS_EMOTION={TOP_KEYWORDS_EMOTION})")
    
    def _encode_multi_hot(self, values: List[str], vocab: List[str]) -> np.ndarray:
        """Encode a list of values as multi-hot vector."""
        result = np.zeros(len(vocab), dtype=np.float32)
        for v in values:
            if v in vocab:
                result[vocab.index(v)] = 1.0
        return result
    
    def _build_features(
        self, 
        tmdb_id: int, 
        movie_features: dict,
        z_score: bool = True
    ) -> Optional[np.ndarray]:
        """
        Build feature vector for a single movie.
        
        Args:
            tmdb_id: TMDB movie ID
            movie_features: Dict with genres, keywords
            z_score: Whether to z-score anchor logits
            
        Returns:
            Feature vector or None if missing embedding
        """
        features = []
        
        # 1. Anchor logits (8 features)
        if tmdb_id not in self.tmdb_to_index:
            return None
        
        movie_emb = self.movie_embeddings[self.tmdb_to_index[tmdb_id]]
        anchor_logits = self._compute_anchor_logits(movie_emb)
        
        if z_score and self.anchor_stats:
            anchor_logits = self._z_score_logits(anchor_logits)
        
        features.extend(anchor_logits)
        
        # 2. Genres multi-hot
        raw_genres = movie_features.get("genres") or []
        if isinstance(raw_genres, str):
            raw_genres = json.loads(raw_genres)
        genre_names = [g.get("name") if isinstance(g, dict) else g for g in raw_genres]
        genre_names = [g for g in genre_names if g]
        genres_encoded = self._encode_multi_hot(genre_names, self.genre_vocab)
        features.extend(genres_encoded)
        
        # 3. Keywords multi-hot
        raw_keywords = movie_features.get("keywords") or []
        if isinstance(raw_keywords, str):
            raw_keywords = json.loads(raw_keywords)
        keyword_names = [k.get("name") if isinstance(k, dict) else k for k in raw_keywords]
        keyword_names = [k for k in keyword_names if k]
        keywords_encoded = self._encode_multi_hot(keyword_names, self.keyword_vocab)
        features.extend(keywords_encoded)
        
        return np.array(features, dtype=np.float32)
    
    def _save_outputs(
        self, 
        X_df: pd.DataFrame, 
        y_df: pd.DataFrame
    ) -> None:
        """Save all outputs to disk."""
        output_dir = Path(EMOTIONS_DATA_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save training data
        X_path = output_dir / "train_X.parquet"
        y_path = output_dir / "train_y.parquet"
        X_df.to_parquet(X_path, index=False)
        y_df.to_parquet(y_path, index=False)
        print(f"\n💾 Saved train_X to {X_path}")
        print(f"💾 Saved train_y to {y_path}")
        
        # Save anchor embeddings
        anchor_path = output_dir / "anchor_embeddings.npy"
        np.save(anchor_path, self.anchor_embeddings)
        print(f"💾 Saved anchor embeddings to {anchor_path}")
        
        # Save anchor stats (for z-scoring at inference)
        stats_path = output_dir / "anchor_stats.json"
        with open(stats_path, "w") as f:
            json.dump(self.anchor_stats, f, indent=2)
        print(f"💾 Saved anchor stats to {stats_path}")
        
        # Save feature schema
        schema = {
            "created_at": datetime.now().isoformat(),
            "feature_order": (
                [f"anchor_{emo}" for emo in PRIMARY_ORDER]
                + [f"genre_{g}" for g in self.genre_vocab]
                + [f"kw_{k}" for k in self.keyword_vocab]
            ),
            "anchor_order": PRIMARY_ORDER,
            "genre_vocab": self.genre_vocab,
            "keyword_vocab": self.keyword_vocab,
            "n_anchor_features": len(PRIMARY_ORDER),
            "n_genre_features": len(self.genre_vocab),
            "n_keyword_features": len(self.keyword_vocab),
            "total_features": len(PRIMARY_ORDER) + len(self.genre_vocab) + len(self.keyword_vocab),
            "class_labels": PRIMARY_ORDER,
            "n_classes": len(PRIMARY_ORDER),
        }
        
        schema_path = output_dir / "feature_schema.json"
        with open(schema_path, "w") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved feature schema to {schema_path}")
    
    def run(self):
        """Execute the full pipeline."""
        print("=" * 70)
        print("Pipeline 05a: Build Emotion Training Dataset")
        print("=" * 70)
        
        # Load embeddings
        self.movie_embeddings, self.tmdb_to_index = self._load_movie_embeddings()
        
        # Encode anchors
        self.anchor_embeddings = self._encode_anchors()
        
        self.db.connect()
        
        try:
            # Step 1: Load emotion labels
            print("\n📖 Loading emotion labels...")
            labels = self.db.get_emotion_labels(label_kind="transmitted")
            self.stats["total_labels"] = len(labels)
            print(f"  Found {len(labels)} labeled movies")
            
            if len(labels) < 10:
                raise ValueError(f"Need at least 10 labeled movies, found {len(labels)}")
            
            # Step 2: Load all movie features
            print("\n📊 Loading movie features...")
            all_features = self.db.fetch_all("SELECT * FROM movie_features")
            features_by_tmdb = {f["tmdb_id"]: f for f in all_features}
            print(f"  Found {len(all_features)} movies with features")
            
            # Step 3: Build vocabularies from ALL features (not just labeled ones)
            self._build_vocabularies(all_features)
            
            # Step 4: First pass - compute raw anchor logits for z-score stats
            print("\n📊 Computing anchor logit statistics...")
            raw_logits_list = []
            valid_labels = []
            
            for label in labels:
                tmdb_id = label["tmdb_id"]
                
                # Check if we have embedding
                if tmdb_id not in self.tmdb_to_index:
                    continue
                
                # Check if we have features
                if tmdb_id not in features_by_tmdb:
                    continue
                
                # Compute raw anchor logits
                movie_emb = self.movie_embeddings[self.tmdb_to_index[tmdb_id]]
                raw_logits = self._compute_anchor_logits(movie_emb)
                raw_logits_list.append(raw_logits)
                valid_labels.append(label)
            
            self.stats["labels_with_embeddings"] = len(valid_labels)
            print(f"  Valid samples with embeddings: {len(valid_labels)}")
            
            if len(valid_labels) < 10:
                raise ValueError(f"Need at least 10 valid samples, found {len(valid_labels)}")
            
            # Compute z-score stats from training data
            raw_logits_matrix = np.array(raw_logits_list)
            self.anchor_stats = self._compute_anchor_stats(raw_logits_matrix)
            print("  Computed z-score statistics for anchor logits")
            
            # Step 5: Build final features (with z-scoring)
            print("\n🔧 Building training features...")
            X_rows = []
            y_rows = []
            tmdb_ids = []
            emotions = []
            
            for label in valid_labels:
                tmdb_id = label["tmdb_id"]
                emotion = label["emotion"]
                
                movie_feats = features_by_tmdb.get(tmdb_id)
                features = self._build_features(tmdb_id, movie_feats, z_score=True)
                
                if features is None:
                    continue
                
                X_rows.append(features)
                y_rows.append(PRIMARY_ORDER.index(emotion))  # Convert to class index
                tmdb_ids.append(tmdb_id)
                emotions.append(emotion)
            
            self.stats["labels_with_features"] = len(X_rows)
            
            # Class distribution
            emotion_counter = Counter(emotions)
            self.stats["class_distribution"] = dict(emotion_counter)
            
            # Step 6: Create DataFrames
            feature_names = (
                [f"anchor_{emo}" for emo in PRIMARY_ORDER]
                + [f"genre_{g}" for g in self.genre_vocab]
                + [f"kw_{k}" for k in self.keyword_vocab]
            )
            
            X_df = pd.DataFrame(X_rows, columns=feature_names)
            X_df["tmdb_id"] = tmdb_ids
            
            y_df = pd.DataFrame({
                "label": y_rows,
                "emotion": emotions,
                "tmdb_id": tmdb_ids
            })
            
            print(f"\n  X shape: {X_df.shape}")
            print(f"  y shape: {y_df.shape}")
            print(f"  Features: {len(feature_names)}")
            
            # Step 7: Save outputs
            self._save_outputs(X_df, y_df)
            
            # Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Total labels in DB:        {self.stats['total_labels']}")
            print(f"Labels with embeddings:    {self.stats['labels_with_embeddings']}")
            print(f"Final training samples:    {self.stats['labels_with_features']}")
            print(f"\nClass distribution:")
            for emo, count in sorted(self.stats["class_distribution"].items(), key=lambda x: -x[1]):
                pct = 100 * count / self.stats["labels_with_features"]
                print(f"  {emo:15} {count:4d} ({pct:5.1f}%)")
            print("=" * 70)
            
        finally:
            self.db.close()


def main():
    """Main entry point."""
    builder = EmotionTrainingDatasetBuilder()
    builder.run()


if __name__ == "__main__":
    main()
