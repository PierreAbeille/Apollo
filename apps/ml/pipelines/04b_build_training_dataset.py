#!/usr/bin/env python3
"""
Pipeline 04b: Build Training Dataset

Constructs X/y training data for XGBoost from:
- interactions (labels from rating/is_done)
- movie_features (lang, genres, keywords)
- embeddings (multi-centroid similarity features)

Labels V1:
- y=1 if is_done=True & rating >= 8
- y=0 if is_done=True & rating <= 5
- Ignore ratings 6-7 (ambiguous signal)

Features V2:
- cos_pos_c0..c4: Cosine to each of 5 positive centroids (KMeans)
- max_cos_pos: Max cosine to any positive centroid
- release_year
- lang one-hot (top 10)
- genres multi-hot (top 20)
- keywords multi-hot (top 300)

Output:
- data/train/X_train.parquet
- data/train/y_train.parquet
- data/train/feature_schema.json
- models/<timestamp>_pos_centroids.npy
"""
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    TRAIN_DATA_DIR,
    MODELS_DIR,
    EMBEDDINGS_DIR,
    POSITIVE_RATING_THRESHOLD,
    NEGATIVE_RATING_THRESHOLD,
    TOP_GENRES,
    TOP_KEYWORDS,
    TOP_LANGUAGES,
    XGBOOST_SEED,
)
from clients.db import DatabaseClient
from features.preference_score import calculate_user_profile
from features.centroid_features import (
    compute_positive_centroids,
    compute_centroid_features,
    get_centroid_feature_names,
    save_centroids,
)
from embeddings.similarity import cosine_similarity


DEFAULT_REGRESSION_CLUSTERS = 4


class TrainingDatasetBuilder:
    """Builds training dataset for XGBoost from DB and embeddings."""

    def __init__(self, n_clusters: int = DEFAULT_REGRESSION_CLUSTERS):
        """Initialize builder."""
        self.db = DatabaseClient()
        self.n_clusters = n_clusters
        
        # Load embeddings
        self.embeddings, self.tmdb_to_index = self._load_embeddings()
        
        # Will be computed during build
        self.positive_centroids = None
        self.centroids_version = None
        self.genre_vocab = []
        self.keyword_vocab = []
        self.lang_vocab = []
        
        # Statistics
        self.stats = {
            "total_interactions": 0,
            "positive_samples": 0,
            "negative_samples": 0,
            "ignored_samples": 0,
            "missing_features": 0,
        }

    def _load_embeddings(self) -> Tuple[np.ndarray, Dict[int, int]]:
        """Load embeddings and mapping."""
        embeddings_path = Path(EMBEDDINGS_DIR) / "movie_embeddings.npy"
        mapping_path = Path(EMBEDDINGS_DIR) / "tmdb_to_index.json"
        
        print(f"📊 Loading embeddings from {EMBEDDINGS_DIR}...")
        embeddings = np.load(embeddings_path)
        with open(mapping_path, "r") as f:
            tmdb_to_index = {int(k): v for k, v in json.load(f).items()}
        print(f"  Loaded {embeddings.shape[0]} embeddings ({embeddings.shape[1]} dims)")
        
        return embeddings, tmdb_to_index

    def _get_label(self, interaction: dict) -> Optional[float]:
        """
        Determine label from interaction for regression.
        Uses raw rating 1-10.
        
        Returns:
            Rating (float) or None if not rated
        """
        rating = interaction.get("rating")
        
        if rating is None:
            return None
            
        return float(rating)

    def _build_vocabularies(self, movie_features: List[dict]) -> None:
        """Build vocabularies for genres, keywords, and languages."""
        print("\n📖 Building feature vocabularies...")
        
        # Count frequencies
        genre_counter = Counter()
        keyword_counter = Counter()
        lang_counter = Counter()
        
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
            
            if feat.get("lang"):
                lang_counter[feat["lang"]] += 1
        
        # Take top N
        self.genre_vocab = [g for g, _ in genre_counter.most_common(TOP_GENRES)]
        self.keyword_vocab = [k for k, _ in keyword_counter.most_common(TOP_KEYWORDS)]
        self.lang_vocab = [l for l, _ in lang_counter.most_common(TOP_LANGUAGES)]
        
        print(f"  Genres: {len(self.genre_vocab)} (from {len(genre_counter)} total)")
        print(f"  Keywords: {len(self.keyword_vocab)} (from {len(keyword_counter)} total)")
        print(f"  Languages: {len(self.lang_vocab)} (from {len(lang_counter)} total)")

    def _encode_multi_hot(self, values: List[str], vocab: List[str]) -> np.ndarray:
        """Encode a list of values as multi-hot vector."""
        result = np.zeros(len(vocab), dtype=np.float32)
        for v in values:
            if v in vocab:
                result[vocab.index(v)] = 1.0
        return result

    def _encode_one_hot(self, value: str, vocab: List[str]) -> np.ndarray:
        """Encode a single value as one-hot vector."""
        result = np.zeros(len(vocab), dtype=np.float32)
        if value in vocab:
            result[vocab.index(value)] = 1.0
        return result

    def _build_features(self, tmdb_id: int, movie_features: dict) -> Optional[np.ndarray]:
        """
        Build feature vector for a single movie.
        
        Args:
            tmdb_id: TMDB movie ID
            movie_features: Dict with lang, genres, keywords from DB
            
        Returns:
            Feature vector or None if missing required data
        """
        features = []
        
        # 1. Multi-centroid cosine features (cos_pos_c0..c4 + max_cos_pos)
        if tmdb_id in self.tmdb_to_index and self.positive_centroids is not None:
            movie_emb = self.embeddings[self.tmdb_to_index[tmdb_id]]
            centroid_feats = compute_centroid_features(movie_emb, self.positive_centroids)
        else:
            centroid_feats = np.zeros(self.n_clusters + 1)
        features.extend(centroid_feats)
        
        # 2. Release year (normalized)
        movie = self.db.get_movie_by_tmdb_id(tmdb_id)
        release_year = movie.get("release_year") if movie else None
        if release_year is None:
            release_year = 2000  # Default
        # Normalize to roughly [-1, 1] range (1900-2100 -> -1 to 1)
        normalized_year = (release_year - 2000) / 50
        features.append(normalized_year)
        
        # 3. Language one-hot
        lang = movie_features.get("lang") or "en"
        lang_encoded = self._encode_one_hot(lang, self.lang_vocab)
        features.extend(lang_encoded)
        
        # 4. Genres multi-hot
        raw_genres = movie_features.get("genres") or []
        if isinstance(raw_genres, str):
            raw_genres = json.loads(raw_genres)
        genre_names = [g.get("name") if isinstance(g, dict) else g for g in raw_genres]
        genre_names = [g for g in genre_names if g]
        genres_encoded = self._encode_multi_hot(genre_names, self.genre_vocab)
        features.extend(genres_encoded)
        
        # 5. Keywords multi-hot
        raw_keywords = movie_features.get("keywords") or []
        if isinstance(raw_keywords, str):
            raw_keywords = json.loads(raw_keywords)
        keyword_names = [k.get("name") if isinstance(k, dict) else k for k in raw_keywords]
        keyword_names = [k for k in keyword_names if k]
        keywords_encoded = self._encode_multi_hot(keyword_names, self.keyword_vocab)
        features.extend(keywords_encoded)
        
        return np.array(features, dtype=np.float32)

    def _save_feature_schema(self) -> None:
        """Save feature schema for reproducible scoring."""
        centroid_feature_names = get_centroid_feature_names(self.n_clusters)
        
        schema = {
            "feature_order": (
                centroid_feature_names
                + ["release_year_normalized"]
                + [f"lang_{l}" for l in self.lang_vocab] 
                + [f"genre_{g}" for g in self.genre_vocab]
                + [f"kw_{k}" for k in self.keyword_vocab]
            ),
            "genre_vocab": self.genre_vocab,
            "keyword_vocab": self.keyword_vocab,
            "lang_vocab": self.lang_vocab,
            "n_clusters": self.n_clusters,
            "centroids_version": self.centroids_version,
            "positive_threshold": POSITIVE_RATING_THRESHOLD,
            "negative_threshold": NEGATIVE_RATING_THRESHOLD,
        }
        
        schema_path = Path(TRAIN_DATA_DIR) / "feature_schema.json"
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved feature schema to {schema_path}")

    def run(self):
        """Main pipeline execution."""
        print("=" * 70)
        print("Pipeline 04b: Build Training Dataset")
        print("=" * 70)
        
        self.db.connect()
        
        try:
            # Step 1: Load all interactions
            print("\n📖 Loading interactions...")
            interactions = self.db.get_all_interactions()
            self.stats["total_interactions"] = len(interactions)
            print(f"  Found {len(interactions)} total interactions")
            
            # Step 2: Identify positive movies and compute centroids
            print("\n🧠 Computing positive centroids (KMeans)...")
            positive_tmdb_ids = [
                i["tmdb_id"] for i in interactions 
                if i.get("is_done") and i.get("rating") and i["rating"] >= POSITIVE_RATING_THRESHOLD
            ]
            print(f"  Found {len(positive_tmdb_ids)} positive movies (rating >= {POSITIVE_RATING_THRESHOLD})")
            
            if len(positive_tmdb_ids) < 2:
                raise ValueError(f"Need at least 2 positive movies, found {len(positive_tmdb_ids)}")
            
            self.positive_centroids, pos_embs = compute_positive_centroids(
                self.embeddings,
                positive_tmdb_ids,
                self.tmdb_to_index,
                n_clusters=self.n_clusters,
                random_state=XGBOOST_SEED
            )
            print(f"  Computed {self.positive_centroids.shape[0]} centroids ({self.positive_centroids.shape[1]} dims)")
            
            # Generate version and save centroids
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.centroids_version = f"centroids_reg_k{self.n_clusters}_{timestamp}"
            centroids_path = save_centroids(
                self.positive_centroids, 
                self.centroids_version, 
                MODELS_DIR
            )
            print(f"  💾 Saved centroids to {centroids_path}")
            
            # Step 3: Load all movie features
            print("\n📊 Loading movie features...")
            all_features = self.db.fetch_all("SELECT * FROM movie_features")
            features_by_tmdb = {f["tmdb_id"]: f for f in all_features}
            print(f"  Found {len(all_features)} movies with features")
            
            # Step 4: Build vocabularies
            self._build_vocabularies(all_features)
            
            # Step 5: Build X and y
            print("\n🔧 Building training samples...")
            X_rows = []
            y_rows = []
            tmdb_ids = []
            
            for interaction in interactions:
                tmdb_id = interaction["tmdb_id"]
                
                # Get label
                label = self._get_label(interaction)
                if label is None:
                    self.stats["ignored_samples"] += 1
                    continue
                
                # Get features
                movie_feats = features_by_tmdb.get(tmdb_id)
                if movie_feats is None:
                    self.stats["missing_features"] += 1
                    continue
                
                features = self._build_features(tmdb_id, movie_feats)
                if features is None:
                    self.stats["missing_features"] += 1
                    continue
                
                X_rows.append(features)
                y_rows.append(label)
                tmdb_ids.append(tmdb_id)
                
                if label >= POSITIVE_RATING_THRESHOLD:
                    self.stats["positive_samples"] += 1
                elif label <= NEGATIVE_RATING_THRESHOLD:
                    self.stats["negative_samples"] += 1
                else:
                    self.stats["ignored_samples"] += 1
            
            # Step 6: Convert to DataFrames
            centroid_feature_names = get_centroid_feature_names(self.n_clusters)
            feature_names = (
                centroid_feature_names
                + ["release_year_normalized"]
                + [f"lang_{l}" for l in self.lang_vocab]
                + [f"genre_{g}" for g in self.genre_vocab]
                + [f"kw_{k}" for k in self.keyword_vocab]
            )
            
            X_df = pd.DataFrame(X_rows, columns=feature_names)
            X_df["tmdb_id"] = tmdb_ids
            
            y_df = pd.DataFrame({"label": y_rows, "tmdb_id": tmdb_ids})
            
            print(f"\n  X shape: {X_df.shape}")
            print(f"  y shape: {y_df.shape}")
            print(f"  Feature count: {len(feature_names)}")
            
            # Step 7: Save to Parquet
            X_path = Path(TRAIN_DATA_DIR) / "X_train.parquet"
            y_path = Path(TRAIN_DATA_DIR) / "y_train.parquet"
            
            X_df.to_parquet(X_path, index=False)
            y_df.to_parquet(y_path, index=False)
            
            print(f"\n💾 Saved X_train to {X_path}")
            print(f"💾 Saved y_train to {y_path}")
            
            # Step 8: Save feature schema
            self._save_feature_schema()
            
            # Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Total interactions:        {self.stats['total_interactions']}")
            print(f"✓ Samples with rating:     {len(y_rows)}")
            print(f"  - High (>= {POSITIVE_RATING_THRESHOLD}): {self.stats['positive_samples']}")
            print(f"  - Low (<= {NEGATIVE_RATING_THRESHOLD}):  {self.stats['negative_samples']}")
            print(f"  - Mid (6-7):             {self.stats['ignored_samples']}")
            print(f"✗ Missing features:        {self.stats['missing_features']}")
            print(f"\nAverage Rating: {np.mean(y_rows):.2f}")
            print("=" * 70)
            
        finally:
            self.db.close()


if __name__ == "__main__":
    TrainingDatasetBuilder().run()
