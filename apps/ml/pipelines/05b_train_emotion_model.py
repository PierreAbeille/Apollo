#!/usr/bin/env python3
"""
Pipeline 05b: Train Emotion Model

Trains a multinomial Logistic Regression classifier on the emotion dataset.

Model:
- LogisticRegression with softmax (multinomial)
- class_weight="balanced" for imbalanced classes
- Optional isotonic calibration

Metrics:
- Accuracy (top-1)
- Top-2 accuracy
- Macro F1
- Confusion matrix
- Confidence calibration analysis

Output:
- models/emotion_v{version}.pkl
- models/emotion_v{version}_schema.json
- models/emotion_v{version}_metrics.json
"""
import sys
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import EMOTIONS_DATA_DIR, MODELS_DIR, XGBOOST_SEED
from config.emotions import PRIMARY_ORDER

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    confusion_matrix,
    classification_report,
)


class EmotionModelTrainer:
    """Trains and evaluates emotion classification model."""
    
    def __init__(
        self, 
        test_size: float = 0.2,
        random_state: int = XGBOOST_SEED,
        calibrate: bool = False,
        n_cv_folds: int = 5,
    ):
        """
        Initialize trainer.
        
        Args:
            test_size: Fraction of data for test set
            random_state: Random seed for reproducibility
            calibrate: Whether to apply isotonic calibration
            n_cv_folds: Number of cross-validation folds
        """
        self.test_size = test_size
        self.random_state = random_state
        self.calibrate = calibrate
        self.n_cv_folds = n_cv_folds
        
        # Will be loaded/computed
        self.model = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.feature_names = None
        self.class_labels = PRIMARY_ORDER
        
        # Results
        self.metrics = {}
        self.version = None
    
    def _load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load training data from parquet files."""
        X_path = Path(EMOTIONS_DATA_DIR) / "train_X.parquet"
        y_path = Path(EMOTIONS_DATA_DIR) / "train_y.parquet"
        
        if not X_path.exists():
            raise FileNotFoundError(f"Training data not found: {X_path}")
        
        X_df = pd.read_parquet(X_path)
        y_df = pd.read_parquet(y_path)
        
        print(f"✓ Loaded training data: X={X_df.shape}, y={y_df.shape}")
        return X_df, y_df
    
    def _prepare_data(self, X_df: pd.DataFrame, y_df: pd.DataFrame) -> None:
        """Prepare train/test split."""
        # Extract tmdb_id and features
        self.feature_names = [c for c in X_df.columns if c != "tmdb_id"]
        X = X_df[self.feature_names].values
        y = y_df["label"].values
        
        # Stratified split
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=y
        )
        
        print(f"\n📊 Data split:")
        print(f"  Train: {len(self.X_train)} samples")
        print(f"  Test:  {len(self.X_test)} samples")
        
        # Show class balance
        train_counts = pd.Series(self.y_train).value_counts().sort_index()
        print(f"\n  Training class counts:")
        for idx, count in train_counts.items():
            emo = self.class_labels[idx]
            print(f"    {emo:15} {count:4d}")
    
    def _train_model(self) -> None:
        """Train logistic regression model."""
        print("\n🔧 Training LogisticRegression (multinomial)...")
        
        base_model = LogisticRegression(
            solver="lbfgs",
            class_weight="balanced",
            max_iter=2000,
            random_state=self.random_state,
        )
        
        if self.calibrate:
            print("  Applying isotonic calibration...")
            self.model = CalibratedClassifierCV(
                base_model,
                method="isotonic",
                cv=min(5, len(np.unique(self.y_train))),
            )
        else:
            self.model = base_model
        
        # Cross-validation score
        print(f"\n  Running {self.n_cv_folds}-fold cross-validation...")
        cv = StratifiedKFold(n_splits=self.n_cv_folds, shuffle=True, random_state=self.random_state)
        
        # Use base_model for CV if calibrating (calibration is applied after)
        cv_model = base_model if self.calibrate else self.model
        cv_scores = cross_val_score(cv_model, self.X_train, self.y_train, cv=cv, scoring="accuracy")
        
        self.metrics["cv_accuracy_mean"] = float(np.mean(cv_scores))
        self.metrics["cv_accuracy_std"] = float(np.std(cv_scores))
        print(f"  CV Accuracy: {np.mean(cv_scores):.3f} ± {np.std(cv_scores):.3f}")
        
        # Train final model on full training set
        print("\n  Training final model on full training set...")
        self.model.fit(self.X_train, self.y_train)
        print("✓ Model trained")
    
    def _evaluate_model(self) -> None:
        """Evaluate model on test set."""
        print("\n📈 Evaluating on test set...")
        
        # Predictions
        y_pred = self.model.predict(self.X_test)
        y_proba = self.model.predict_proba(self.X_test)
        
        # Top-1 accuracy
        acc = accuracy_score(self.y_test, y_pred)
        self.metrics["accuracy"] = float(acc)
        print(f"  Accuracy (top-1): {acc:.3f}")
        
        # Top-2 accuracy
        top2_correct = 0
        for i, true_label in enumerate(self.y_test):
            top2_preds = np.argsort(y_proba[i])[-2:]
            if true_label in top2_preds:
                top2_correct += 1
        top2_acc = top2_correct / len(self.y_test)
        self.metrics["top2_accuracy"] = float(top2_acc)
        print(f"  Accuracy (top-2): {top2_acc:.3f}")
        
        # Macro F1
        f1 = f1_score(self.y_test, y_pred, average="macro")
        self.metrics["macro_f1"] = float(f1)
        print(f"  Macro F1:         {f1:.3f}")
        
        # Confusion matrix
        cm = confusion_matrix(self.y_test, y_pred)
        self.metrics["confusion_matrix"] = cm.tolist()
        
        # Classification report
        print("\n  Classification Report:")
        labels = list(range(len(self.class_labels)))
        report = classification_report(
            self.y_test, y_pred,
            labels=labels,
            target_names=self.class_labels,
            zero_division=0
        )
        print(report)
        
        # Store per-class metrics
        self.metrics["per_class"] = {}
        for i, emo in enumerate(self.class_labels):
            mask = self.y_test == i
            if mask.sum() > 0:
                class_acc = (y_pred[mask] == i).mean()
                self.metrics["per_class"][emo] = {
                    "accuracy": float(class_acc),
                    "support": int(mask.sum()),
                }
    
    def _analyze_confidence(self) -> None:
        """Analyze confidence calibration."""
        print("\n🎯 Confidence calibration analysis...")
        
        y_proba = self.model.predict_proba(self.X_test)
        
        # Confidence = max probability - second max probability
        confidences = []
        for probs in y_proba:
            sorted_probs = np.sort(probs)[::-1]
            conf = sorted_probs[0] - sorted_probs[1]
            confidences.append(conf)
        confidences = np.array(confidences)
        
        # Bucket analysis
        buckets = [
            (0.00, 0.05, "0.00-0.05"),
            (0.05, 0.10, "0.05-0.10"),
            (0.10, 0.20, "0.10-0.20"),
            (0.20, 1.00, "0.20+"),
        ]
        
        y_pred = self.model.predict(self.X_test)
        correct = (y_pred == self.y_test)
        
        calibration_results = []
        print(f"\n  {'Bucket':12} {'Count':>6} {'Accuracy':>10}")
        print("  " + "-" * 32)
        
        for low, high, name in buckets:
            mask = (confidences >= low) & (confidences < high)
            count = mask.sum()
            if count > 0:
                bucket_acc = correct[mask].mean()
                print(f"  {name:12} {count:6d} {bucket_acc:10.3f}")
                calibration_results.append({
                    "bucket": name,
                    "count": int(count),
                    "accuracy": float(bucket_acc),
                })
            else:
                print(f"  {name:12} {0:6d} {'N/A':>10}")
        
        self.metrics["confidence_calibration"] = calibration_results
        self.metrics["avg_confidence"] = float(np.mean(confidences))
        print(f"\n  Average confidence: {np.mean(confidences):.3f}")
    
    def _save_model(self) -> None:
        """Save model and metadata."""
        # Generate version
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.version = f"emotion_v{timestamp}"
        
        # Save model
        model_path = Path(MODELS_DIR) / f"{self.version}.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(self.model, f)
        print(f"\n💾 Saved model to {model_path}")
        
        # Save schema
        schema = {
            "version": self.version,
            "created_at": datetime.now().isoformat(),
            "feature_names": self.feature_names,
            "class_labels": self.class_labels,
            "n_features": len(self.feature_names),
            "n_classes": len(self.class_labels),
            "calibrated": self.calibrate,
            "model_type": "LogisticRegression",
        }
        
        schema_path = Path(MODELS_DIR) / f"{self.version}_schema.json"
        with open(schema_path, "w") as f:
            json.dump(schema, f, indent=2)
        print(f"💾 Saved schema to {schema_path}")
        
        # Save metrics
        self.metrics["version"] = self.version
        self.metrics["created_at"] = datetime.now().isoformat()
        self.metrics["train_size"] = len(self.X_train)
        self.metrics["test_size"] = len(self.X_test)
        
        metrics_path = Path(MODELS_DIR) / f"{self.version}_metrics.json"
        with open(metrics_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        print(f"💾 Saved metrics to {metrics_path}")
    
    def run(self):
        """Execute the full training pipeline."""
        print("=" * 70)
        print("Pipeline 05b: Train Emotion Model")
        print("=" * 70)
        
        # Load data
        X_df, y_df = self._load_data()
        
        # Prepare train/test split
        self._prepare_data(X_df, y_df)
        
        # Train model
        self._train_model()
        
        # Evaluate
        self._evaluate_model()
        
        # Confidence analysis
        self._analyze_confidence()
        
        # Save
        self._save_model()
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Model version:       {self.version}")
        print(f"Training samples:    {len(self.X_train)}")
        print(f"Test samples:        {len(self.X_test)}")
        print(f"Features:            {len(self.feature_names)}")
        print(f"\nMetrics:")
        print(f"  CV Accuracy:       {self.metrics['cv_accuracy_mean']:.3f} ± {self.metrics['cv_accuracy_std']:.3f}")
        print(f"  Test Accuracy:     {self.metrics['accuracy']:.3f}")
        print(f"  Top-2 Accuracy:    {self.metrics['top2_accuracy']:.3f}")
        print(f"  Macro F1:          {self.metrics['macro_f1']:.3f}")
        print("=" * 70)
        
        return self.metrics


def main():
    """Main entry point."""
    trainer = EmotionModelTrainer(
        test_size=0.2,
        calibrate=False,  # Start without calibration
    )
    trainer.run()


if __name__ == "__main__":
    main()
