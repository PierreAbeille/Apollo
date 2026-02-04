#!/usr/bin/env python3
"""
Pipeline 04c: Train and Score XGBoost

1. Loads X_train.parquet and y_train.parquet
2. Splits data (stratified)
3. Trains XGBClassifier
4. Evaluates: AUC, PR-AUC
5. Saves model to models/xgb_taste_v{date}.json
6. Loads candidate_pool.json
7. Rebuilds features using feature_schema.json
8. Scores candidates with predict_proba
9. Inserts into taste_candidates with model_version

Usage:
    python 04c_train_and_score_xgboost.py [--train-only] [--score-only]
"""
import sys
import json
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    TRAIN_DATA_DIR,
    MODELS_DIR,
    CACHE_DIR,
    EMBEDDINGS_DIR,
    MAX_TASTE_CANDIDATES,
    XGBOOST_SEED,
    XGBOOST_TEST_SIZE,
    XGBOOST_N_ESTIMATORS,
    XGBOOST_MAX_DEPTH,
    XGBOOST_LEARNING_RATE,
    MMR_ENABLED,
    MMR_LAMBDA,
    MMR_TOP_K,
)
from clients.db import DatabaseClient
from features.centroid_features import (
    compute_centroid_features,
    load_centroids,
    get_centroid_feature_names,
)
from features.mmr_reranker import mmr_rerank, compute_diversity_score

# XGBoost and sklearn imports
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


# Paths
CANDIDATE_POOL_PATH = Path(CACHE_DIR) / "candidate_pool.json"
FEATURE_SCHEMA_PATH = Path(TRAIN_DATA_DIR) / "feature_schema.json"


class XGBoostTrainerScorer:
    """Trains XGBoost model and scores candidates."""

    def __init__(self):
        """Initialize trainer/scorer."""
        self.db = DatabaseClient()
        self.model = None
        self.model_version = None
        self.feature_schema = None
        
        # Embeddings for centroid features
        self.embeddings = None
        self.tmdb_to_index = None
        self.positive_centroids = None
        self.negative_centroid = None  # V1.5
        self.n_clusters = None
        
        # Statistics
        self.stats = {
            "train_samples": 0,
            "test_samples": 0,
            "auc_roc": 0.0,
            "auc_pr": 0.0,
            "candidates_scored": 0,
            "candidates_saved": 0,
        }

    def _load_training_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load training data from Parquet files."""
        print("\n📊 Loading training data...")
        
        X_path = Path(TRAIN_DATA_DIR) / "X_train.parquet"
        y_path = Path(TRAIN_DATA_DIR) / "y_train.parquet"
        
        if not X_path.exists() or not y_path.exists():
            raise FileNotFoundError(
                f"Training data not found. Run 04b_build_training_dataset.py first."
            )
        
        X_df = pd.read_parquet(X_path)
        y_df = pd.read_parquet(y_path)
        
        print(f"  X shape: {X_df.shape}")
        print(f"  y shape: {y_df.shape}")
        print(f"  Average rating: {y_df['label'].mean():.2f}")
        
        return X_df, y_df

    def _load_feature_schema(self) -> dict:
        """Load feature schema for consistent feature building."""
        print("\n📖 Loading feature schema...")
        
        if not FEATURE_SCHEMA_PATH.exists():
            raise FileNotFoundError(
                f"Feature schema not found at {FEATURE_SCHEMA_PATH}. "
                "Run 04b_build_training_dataset.py first."
            )
        
        with open(FEATURE_SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema = json.load(f)
        
        print(f"  Genres: {len(schema['genre_vocab'])}")
        print(f"  Keywords: {len(schema['keyword_vocab'])}")
        print(f"  Languages: {len(schema['lang_vocab'])}")
        print(f"  Total features: {len(schema['feature_order'])}")
        
        return schema

    def _load_embeddings_and_centroids(self) -> None:
        """Load embeddings and positive centroids."""
        print("\n🧠 Loading embeddings and centroids...")
        
        embeddings_path = Path(EMBEDDINGS_DIR) / "movie_embeddings.npy"
        mapping_path = Path(EMBEDDINGS_DIR) / "tmdb_to_index.json"
        
        self.embeddings = np.load(embeddings_path)
        with open(mapping_path, "r") as f:
            self.tmdb_to_index = {int(k): v for k, v in json.load(f).items()}
        
        print(f"  Loaded {self.embeddings.shape[0]} embeddings")
        
        # Load feature schema to get centroids version
        if self.feature_schema is None:
            self.feature_schema = self._load_feature_schema()
        
        # Load centroids (V1.5: includes negative centroid)
        centroids_version = self.feature_schema.get("centroids_version")
        if centroids_version:
            self.positive_centroids, self.negative_centroid = load_centroids(
                centroids_version, 
                MODELS_DIR,
                load_negative=True
            )
            self.n_clusters = self.feature_schema.get("n_clusters", 5)
            print(f"  Loaded centroids: {centroids_version}")
            print(f"  Positive centroids shape: {self.positive_centroids.shape}")
            if self.negative_centroid is not None:
                print(f"  Negative centroid loaded (V1.5)")
        else:
            raise ValueError("No centroids_version found in feature schema")

    def _generate_model_version(self) -> str:
        """Generate a unique model version identifier."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_str = f"{XGBOOST_N_ESTIMATORS}_{XGBOOST_MAX_DEPTH}_{XGBOOST_LEARNING_RATE}"
        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:6]
        return f"xgb_reg_v{timestamp}_{config_hash}"

    def train(self) -> None:
        """Train XGBoost model."""
        print("\n" + "=" * 70)
        print("TRAINING PHASE")
        print("=" * 70)
        
        # Load data
        X_df, y_df = self._load_training_data()
        self.feature_schema = self._load_feature_schema()
        
        # Prepare arrays (exclude tmdb_id column)
        feature_cols = [c for c in X_df.columns if c != "tmdb_id"]
        X = X_df[feature_cols].values
        y = y_df["label"].values
        
        # Split
        print(f"\n🔀 Splitting data ({1-XGBOOST_TEST_SIZE:.0%} train / {XGBOOST_TEST_SIZE:.0%} test)...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=XGBOOST_TEST_SIZE, 
            random_state=XGBOOST_SEED
        )
        
        self.stats["train_samples"] = len(X_train)
        self.stats["test_samples"] = len(X_test)
        print(f"  Train: {len(X_train)} samples")
        print(f"  Test: {len(X_test)} samples")
        
        # Train - Ordinal Classification (Phase 13)
        print(f"\n🚀 Training XGBClassifier (Ordinal Multi-class)...")
        print(f"  n_estimators: {XGBOOST_N_ESTIMATORS}")
        print(f"  max_depth: {XGBOOST_MAX_DEPTH}")
        print(f"  learning_rate: {XGBOOST_LEARNING_RATE}")
        print(f"  n_classes: 10 (ratings 1-10)")
        
        # Convert ratings to contiguous classes (XGBoost requires 0-based labels)
        from sklearn.preprocessing import LabelEncoder
        self.label_encoder = LabelEncoder()
        y_train_cls = self.label_encoder.fit_transform(y_train)
        y_test_cls = self.label_encoder.transform(y_test)
        n_classes = len(self.label_encoder.classes_)
        
        print(f"  n_classes: {n_classes} (ratings: {sorted(self.label_encoder.classes_)})")
        
        self.model = xgb.XGBClassifier(
            n_estimators=XGBOOST_N_ESTIMATORS,
            max_depth=XGBOOST_MAX_DEPTH,
            learning_rate=XGBOOST_LEARNING_RATE,
            random_state=XGBOOST_SEED,
            num_class=n_classes,
            objective="multi:softmax",
            eval_metric="mlogloss",
            verbosity=1,
        )
        
        self.model.fit(
            X_train, y_train_cls,
            eval_set=[(X_test, y_test_cls)],
            verbose=True,
        )
        
        # Evaluate
        print("\n📈 Evaluating model...")
        y_pred_cls = self.model.predict(X_test)
        y_pred = self.label_encoder.inverse_transform(y_pred_cls)  # Convert back to original ratings
        
        # Calculate metrics treating predictions as ordinal
        from sklearn.metrics import accuracy_score, classification_report
        accuracy = accuracy_score(y_test, y_pred)
        
        # Also compute "within 1" accuracy (ordinal tolerance)
        within_1 = np.mean(np.abs(y_test - y_pred) <= 1)
        within_2 = np.mean(np.abs(y_test - y_pred) <= 2)
        mae = mean_absolute_error(y_test, y_pred)
        
        self.stats["auc_roc"] = accuracy
        self.stats["auc_pr"] = mae
        
        print(f"\n  🎯 Exact Accuracy: {accuracy:.2%}")
        print(f"  🎯 Within ±1: {within_1:.2%}")
        print(f"  🎯 Within ±2: {within_2:.2%}")
        print(f"  🎯 MAE: {mae:.2f}")
        
        # Feature importance (top 20)
        print("\n📊 Top 20 Feature Importances:")
        importances = self.model.feature_importances_
        importance_df = pd.DataFrame({
            "feature": feature_cols,
            "importance": importances
        }).sort_values("importance", ascending=False)
        
        for i, row in importance_df.head(20).iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")
        
        # Save model
        self.model_version = self._generate_model_version()
        model_path = Path(MODELS_DIR) / f"{self.model_version}.json"
        self.model.save_model(str(model_path))

    def _build_candidate_features(self, tmdb_id: int) -> Optional[np.ndarray]:
        """Build feature vector for a candidate movie using the schema."""
        features = []
        
        # 1. Multi-centroid cosine features (V1.5: includes min, mean, neg, margin)
        if tmdb_id in self.tmdb_to_index and self.positive_centroids is not None:
            movie_emb = self.embeddings[self.tmdb_to_index[tmdb_id]]
            centroid_feats = compute_centroid_features(
                movie_emb, 
                self.positive_centroids,
                self.negative_centroid  # V1.5
            )
        else:
            # Number of features: n_clusters + 3 (max, min, mean) + 2 (neg, margin) if negative exists
            n_feats = self.n_clusters + 3 + (2 if self.negative_centroid is not None else 0)
            centroid_feats = np.zeros(n_feats)
        features.extend(centroid_feats)
        
        # 2. Release year (normalized)
        movie = self.db.get_movie_by_tmdb_id(tmdb_id)
        release_year = movie.get("release_year") if movie else None
        if release_year is None:
            release_year = 2000
        normalized_year = (release_year - 2000) / 50
        features.append(normalized_year)
        
        # 3. Get movie features from DB
        movie_feats = self.db.fetch_one(
            "SELECT lang, genres, keywords, production_countries FROM movie_features WHERE tmdb_id = %s",
            (tmdb_id,)
        )
        
        if movie_feats is None:
            return None
        
        # 4. Language one-hot
        lang = movie_feats.get("lang") or "en"
        lang_vocab = self.feature_schema["lang_vocab"]
        # Use simple iteration or index lookup
        for l in lang_vocab:
            features.append(1.0 if lang == l else 0.0)
        
        # 5. Genres multi-hot
        raw_genres = movie_feats.get("genres") or []
        if isinstance(raw_genres, str):
            raw_genres = json.loads(raw_genres)
        genre_names = set()
        for g in raw_genres:
            name = g.get("name") if isinstance(g, dict) else g
            if name:
                genre_names.add(name)
        
        genre_vocab = self.feature_schema["genre_vocab"]
        for g in genre_vocab:
            features.append(1.0 if g in genre_names else 0.0)
        
        # 6. Keywords multi-hot
        raw_keywords = movie_feats.get("keywords") or []
        if isinstance(raw_keywords, str):
            raw_keywords = json.loads(raw_keywords)
        keyword_names = set()
        for k in raw_keywords:
            name = k.get("name") if isinstance(k, dict) else k
            if name:
                keyword_names.add(name)
        
        keyword_vocab = self.feature_schema["keyword_vocab"]
        for k in keyword_vocab:
            features.append(1.0 if k in keyword_names else 0.0)
        
        # Decade one-hot
        decade_vocab = self.feature_schema["decade_vocab"]
        
        if release_year:
            decade = (release_year // 10) * 10
            for d in decade_vocab:
                features.append(1.0 if decade == d else 0.0)
        else:
            # If no year, all zeros
            features.extend([0.0] * len(decade_vocab))
        
        return np.array(features, dtype=np.float32)

    def score_candidates(self) -> None:
        """Score candidates using trained model."""
        print("\n" + "=" * 70)
        print("SCORING PHASE")
        print("=" * 70)
        
        # Load candidate pool
        print("\n📖 Loading candidate pool...")
        if not CANDIDATE_POOL_PATH.exists():
            raise FileNotFoundError(
                f"Candidate pool not found at {CANDIDATE_POOL_PATH}. "
                "Run 04a_build_candidate_pool.py first."
            )
        
        with open(CANDIDATE_POOL_PATH, "r") as f:
            pool = json.load(f)
        
        candidate_ids = pool["candidates"]
        print(f"  Loaded {len(candidate_ids)} candidates")
        
        # Load feature schema if not already loaded
        if self.feature_schema is None:
            self.feature_schema = self._load_feature_schema()
        
        # Load model if not already loaded
        if self.model is None:
            print("\n🔄 Loading latest model...")
            model_files = sorted(Path(MODELS_DIR).glob("xgb_*.json"), reverse=True)
            if not model_files:
                raise FileNotFoundError(
                    f"No model found in {MODELS_DIR}. Run training first."
                )
            model_path = model_files[0]
            self.model = xgb.XGBClassifier()
            self.model.load_model(str(model_path))
            self.model_version = model_path.stem
            print(f"  Loaded: {model_path.name}")
        
        # Build features and score
        print("\n🔧 Building features and scoring...")
        scored_candidates = []
        skipped = 0
        
        for i, tmdb_id in enumerate(candidate_ids):
            features = self._build_candidate_features(tmdb_id)
            
            if features is None:
                skipped += 1
                continue
            
            # Compute expected rating using class probabilities (Option 1)
            # E[rating] = Σ (probability_class × rating_value)
            probas = self.model.predict_proba(features.reshape(1, -1))[0]
            
            # Get the actual rating values for each class
            if hasattr(self, 'label_encoder') and self.label_encoder is not None:
                class_values = self.label_encoder.classes_
            else:
                # Fallback: assume classes 0-8 map to ratings 2-10
                class_values = np.arange(2, 11)
            
            # Calculate expected rating as weighted sum
            expected_rating = float(np.sum(probas * class_values))
            scored_candidates.append((tmdb_id, expected_rating))
            
            if (i + 1) % 100 == 0:
                print(f"  [{i+1}/{len(candidate_ids)}] Scored...")
        
        self.stats["candidates_scored"] = len(scored_candidates)
        print(f"\n  Scored: {len(scored_candidates)}")
        print(f"  Skipped (missing features): {skipped}")
        
        # Sort by score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # V1.5: MMR Reranking for diversity
        if MMR_ENABLED and len(scored_candidates) > 10:
            print(f"\n🔄 Applying MMR reranking (λ={MMR_LAMBDA}, top_k={MMR_TOP_K})...")
            
            # Compute diversity before
            div_before = compute_diversity_score(
                scored_candidates,
                self.embeddings,
                self.tmdb_to_index,
                top_n=10
            )
            
            # Rerank
            reranked = mmr_rerank(
                scored_candidates,
                self.embeddings,
                self.tmdb_to_index,
                top_k=MMR_TOP_K,
                lambda_param=MMR_LAMBDA
            )
            
            # Compute diversity after
            div_after = compute_diversity_score(
                reranked,
                self.embeddings,
                self.tmdb_to_index,
                top_n=10
            )
            
            print(f"  Diversity (top-10): {div_before:.2%} → {div_after:.2%}")
            
            # Use reranked list
            top_candidates = reranked[:MAX_TASTE_CANDIDATES]
        else:
            top_candidates = scored_candidates[:MAX_TASTE_CANDIDATES]
        
        # Insert into database
        print(f"\n💾 Inserting top {len(top_candidates)} candidates into taste_candidates...")
        self.db.clear_taste_candidates()
        self.db.insert_taste_candidates(top_candidates, self.model_version)
        self.stats["candidates_saved"] = len(top_candidates)
        
        # Show top 10
        print(f"\n🎬 TOP 10 RECOMMENDATIONS:")
        for i, (tmdb_id, score) in enumerate(top_candidates[:10], 1):
            movie = self.db.get_movie_by_tmdb_id(tmdb_id)
            title = movie["title"] if movie else f"ID:{tmdb_id}"
            year = movie.get("release_year", "?") if movie else "?"
            print(f"  {i}. {title} ({year}) - Score: {score:.4f}")

    def run(self, train_only: bool = False, score_only: bool = False):
        """Main pipeline execution."""
        print("=" * 70)
        print("Pipeline 04c: Train and Score XGBoost")
        print("=" * 70)
        
        self.db.connect()
        
        try:
            # Load embeddings and centroids for feature building
            self._load_embeddings_and_centroids()
            
            if not score_only:
                self.train()
            
            if not train_only:
                self.score_candidates()
            
            # Summary
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            if not score_only:
                print(f"Training samples:     {self.stats['train_samples']}")
                print(f"Test samples:         {self.stats['test_samples']}")
                print(f"🎯 RMSE:              {self.stats['auc_roc']:.4f}")
                print(f"🎯 MAE:               {self.stats['auc_pr']:.4f}")
            if not train_only:
                print(f"Candidates scored:    {self.stats['candidates_scored']}")
                print(f"Candidates saved:     {self.stats['candidates_saved']}")
            print(f"Model version:        {self.model_version}")
            print("=" * 70)
            
        finally:
            self.db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train and score XGBoost model")
    parser.add_argument("--train-only", action="store_true", 
                        help="Only train, don't score candidates")
    parser.add_argument("--score-only", action="store_true",
                        help="Only score candidates using latest model")
    args = parser.parse_args()
    
    trainer = XGBoostTrainerScorer()
    trainer.run(train_only=args.train_only, score_only=args.score_only)
