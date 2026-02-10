#!/usr/bin/env python3
"""
Grid Balancing Lab — Ablation + Balancing Explorer

Identifies which feature blocks and balancing strategies actually improve
performance (taste + emotion), avoiding misleading optimizations.

Output:
  - reports/gridlab_<task>_<timestamp>.json
  - reports/gridlab_<task>_<timestamp>.md

Usage:
  python tools/gridlab.py --task taste --dry-run
  python tools/gridlab.py --task taste --cv 5 --seed 42 --output reports/
  python tools/gridlab.py --task emotion --balancing none,class_weight
"""
import sys
import json
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    TRAIN_DATA_DIR,
    EMOTIONS_DATA_DIR,
    XGBOOST_SEED,
    XGBOOST_N_ESTIMATORS,
    XGBOOST_MAX_DEPTH,
    XGBOOST_LEARNING_RATE,
)

# sklearn
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    accuracy_score,
    f1_score,
    confusion_matrix,
)
import xgboost as xgb


# =============================================================================
# CONSTANTS
# =============================================================================

VERSION = "1.0.0"

# Feature block definitions — maps block ID to column prefix patterns
TASTE_BLOCKS = {
    "COS_POS": {
        "description": "Cosine similarity to positive centroids + max/min/mean",
        "prefixes": ["cos_pos_c", "max_cos_pos", "min_cos_pos", "mean_cos_pos"],
    },
    "NEG": {
        "description": "Negative centroid distance + margin",
        "prefixes": ["cos_to_neg_center", "pos_neg_margin"],
    },
    "META": {
        "description": "Language + decade + release year normalized",
        "prefixes": ["lang_", "decade_", "release_year_normalized"],
    },
    "GENRE": {
        "description": "Genre multi-hot encoding",
        "prefixes": ["genre_"],
    },
    "KW": {
        "description": "Keyword multi-hot encoding (top N)",
        "prefixes": ["kw_"],
    },
}

EMOTION_BLOCKS = {
    "ANCHOR": {
        "description": "Anchor logits (z-scored cosine to 8 emotion anchors)",
        "prefixes": ["anchor_"],
    },
    "GENRE": {
        "description": "Genre multi-hot encoding",
        "prefixes": ["genre_"],
    },
    "KW": {
        "description": "Keyword multi-hot encoding (top N)",
        "prefixes": ["kw_"],
    },
}

# Default ablation configs
TASTE_DEFAULT_CONFIGS = [
    ["COS_POS"],
    ["COS_POS", "NEG"],
    ["COS_POS", "META"],
    ["COS_POS", "META", "GENRE"],
    ["COS_POS", "META", "GENRE", "KW"],  # kw_size will vary
]

EMOTION_DEFAULT_CONFIGS = [
    ["ANCHOR"],
    ["ANCHOR", "GENRE"],
    ["ANCHOR", "GENRE", "KW"],  # kw_size will vary
]

VALID_BALANCING = ["none", "class_weight", "undersample"]

# Safety cap
DEFAULT_MAX_CONFIGS = 20


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ExperimentConfig:
    """Single experiment configuration."""
    config_id: str
    task: str
    blocks: List[str]
    kw_size: int
    balancing: str
    feature_columns: List[str] = field(default_factory=list)
    n_features: int = 0


@dataclass
class FoldResult:
    """Result from a single CV fold."""
    fold: int
    metrics: Dict[str, float]


@dataclass
class ExperimentResult:
    """Aggregated result for one experiment config."""
    config: ExperimentConfig
    fold_results: List[FoldResult]
    mean_metrics: Dict[str, float]
    std_metrics: Dict[str, float]
    cv_coefficient: Dict[str, float]  # std/mean — stability indicator


# =============================================================================
# DATA LOADER
# =============================================================================

def load_dataset(task: str) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Load X, y, and feature schema for a task.

    Returns:
        (X_df, y_df, schema)
    """
    if task == "taste":
        data_dir = Path(TRAIN_DATA_DIR)
        X_path = data_dir / "X_train.parquet"
        y_path = data_dir / "y_train.parquet"
        schema_path = data_dir / "feature_schema.json"
    elif task == "emotion":
        data_dir = Path(EMOTIONS_DATA_DIR)
        X_path = data_dir / "train_X.parquet"
        y_path = data_dir / "train_y.parquet"
        schema_path = data_dir / "feature_schema.json"
    else:
        raise ValueError(f"Unknown task: {task}")

    if not X_path.exists():
        raise FileNotFoundError(f"Training data not found: {X_path}")

    X_df = pd.read_parquet(X_path)
    y_df = pd.read_parquet(y_path)

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    return X_df, y_df, schema


def select_features(
    X_df: pd.DataFrame,
    schema: dict,
    blocks: List[str],
    kw_size: int,
    task: str,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Select feature columns matching the requested blocks.

    Args:
        X_df: Full feature DataFrame
        schema: Feature schema dict
        blocks: List of block IDs (e.g. ["COS_POS", "META", "GENRE"])
        kw_size: Number of keywords to include (0 = skip KW)
        task: "taste" or "emotion"

    Returns:
        (filtered X_df, list of selected column names)
    """
    block_defs = TASTE_BLOCKS if task == "taste" else EMOTION_BLOCKS
    all_feature_cols = [c for c in X_df.columns if c != "tmdb_id"]

    # Gather keyword vocab for slicing
    keyword_vocab = schema.get("keyword_vocab", [])

    selected = []
    for block_id in blocks:
        if block_id not in block_defs:
            raise ValueError(f"Unknown block '{block_id}' for task '{task}'")

        prefixes = block_defs[block_id]["prefixes"]

        if block_id == "KW":
            if kw_size <= 0:
                continue
            # Slice keyword vocab to top N
            kw_subset = keyword_vocab[:kw_size]
            kw_col_names = {f"kw_{k}" for k in kw_subset}
            for col in all_feature_cols:
                if col.startswith("kw_") and col in kw_col_names:
                    if col not in selected:
                        selected.append(col)
        else:
            for col in all_feature_cols:
                for prefix in prefixes:
                    if col == prefix or col.startswith(prefix):
                        if col not in selected:
                            selected.append(col)
                        break

    return X_df[selected], selected


# =============================================================================
# CONFIG GENERATOR
# =============================================================================

def generate_experiment_id(task: str, blocks: List[str], kw_size: int, balancing: str) -> str:
    """Generate a stable experiment ID string."""
    block_str = "+".join(blocks)
    kw_part = f"__KW{kw_size}" if "KW" in blocks and kw_size > 0 else ""
    return f"{task}__{block_str}{kw_part}__bal={balancing}"


def generate_configs(
    task: str,
    kw_sizes: List[int],
    balancing_strategies: List[str],
    X_df: pd.DataFrame,
    schema: dict,
) -> List[ExperimentConfig]:
    """
    Generate the full experiment grid.

    Returns:
        List of ExperimentConfig
    """
    default_configs = TASTE_DEFAULT_CONFIGS if task == "taste" else EMOTION_DEFAULT_CONFIGS
    configs = []

    for blocks in default_configs:
        has_kw = "KW" in blocks

        if has_kw:
            # Generate one config per kw_size (skip 0 since KW is in blocks)
            effective_kw_sizes = [s for s in kw_sizes if s > 0]
            if not effective_kw_sizes:
                effective_kw_sizes = [0]
        else:
            effective_kw_sizes = [0]

        for kw_size in effective_kw_sizes:
            for bal in balancing_strategies:
                # Resolve feature columns
                _, feature_cols = select_features(X_df, schema, blocks, kw_size, task)

                config_id = generate_experiment_id(task, blocks, kw_size, bal)
                configs.append(ExperimentConfig(
                    config_id=config_id,
                    task=task,
                    blocks=blocks,
                    kw_size=kw_size,
                    balancing=bal,
                    feature_columns=feature_cols,
                    n_features=len(feature_cols),
                ))

    return configs


# =============================================================================
# BALANCING
# =============================================================================

def apply_balancing(
    X_train: np.ndarray,
    y_train: np.ndarray,
    strategy: str,
    seed: int,
) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """
    Apply balancing strategy.

    Returns:
        (X_balanced, y_balanced, sample_weights or None)
    """
    if strategy == "none":
        return X_train, y_train, None

    elif strategy == "class_weight":
        # Compute sample weights from class frequencies
        classes, counts = np.unique(y_train, return_counts=True)
        n_samples = len(y_train)
        n_classes = len(classes)
        weights_map = {c: n_samples / (n_classes * cnt) for c, cnt in zip(classes, counts)}
        sample_weights = np.array([weights_map[y] for y in y_train], dtype=np.float32)
        return X_train, y_train, sample_weights

    elif strategy == "undersample":
        # Manual random undersampling (no imblearn dependency)
        rng = np.random.RandomState(seed)
        classes, counts = np.unique(y_train, return_counts=True)
        min_count = int(np.median(counts))  # Use median as target

        indices = []
        for cls in classes:
            cls_indices = np.where(y_train == cls)[0]
            if len(cls_indices) > min_count:
                chosen = rng.choice(cls_indices, size=min_count, replace=False)
            else:
                chosen = cls_indices
            indices.extend(chosen)

        rng.shuffle(indices)
        return X_train[indices], y_train[indices], None

    else:
        raise ValueError(f"Unknown balancing strategy: {strategy}")


# =============================================================================
# METRICS
# =============================================================================

def compute_metrics_taste(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute taste metrics (ordinal classification)."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    exact_acc = accuracy_score(y_true, y_pred)
    within_1 = float(np.mean(np.abs(y_true - y_pred) <= 1))
    within_2 = float(np.mean(np.abs(y_true - y_pred) <= 2))

    return {
        "mae": float(mae),
        "rmse": rmse,
        "exact_accuracy": float(exact_acc),
        "within_1": within_1,
        "within_2": within_2,
    }


def compute_metrics_emotion(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_proba: Optional[np.ndarray],
    n_classes: int,
) -> Dict[str, float]:
    """Compute emotion metrics (multiclass)."""
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)

    # Top-2 accuracy
    top2_acc = 0.0
    if y_proba is not None:
        top2_correct = 0
        for i, true_label in enumerate(y_true):
            top2_preds = np.argsort(y_proba[i])[-2:]
            if true_label in top2_preds:
                top2_correct += 1
        top2_acc = top2_correct / len(y_true)

    # Confusion matrix (as flat list for JSON)
    cm = confusion_matrix(y_true, y_pred, labels=list(range(n_classes)))

    return {
        "accuracy_top1": float(acc),
        "accuracy_top2": float(top2_acc),
        "macro_f1": float(macro_f1),
        "confusion_matrix": cm.tolist(),
    }


# =============================================================================
# CV RUNNER
# =============================================================================

def run_experiment(
    X_full: pd.DataFrame,
    y: np.ndarray,
    config: ExperimentConfig,
    n_folds: int,
    seed: int,
) -> ExperimentResult:
    """
    Run a single experiment config through StratifiedKFold CV.

    Returns:
        ExperimentResult with per-fold and aggregated metrics.
    """
    # Select features for this config
    X = X_full[config.feature_columns].values

    # Stratify: for taste, discretize continuous labels
    if config.task == "taste":
        y_stratify = y.astype(int)
    else:
        y_stratify = y

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    fold_results = []

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y_stratify)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        # Apply balancing
        X_train_bal, y_train_bal, sample_weights = apply_balancing(
            X_train, y_train, config.balancing, seed + fold_idx
        )

        if config.task == "taste":
            metrics = _run_taste_fold(X_train_bal, y_train_bal, X_val, y_val, sample_weights, seed)
        else:
            metrics = _run_emotion_fold(X_train_bal, y_train_bal, X_val, y_val, sample_weights, seed)

        fold_results.append(FoldResult(fold=fold_idx, metrics=metrics))

    # Aggregate — skip non-numeric keys like confusion_matrix
    metric_keys = [k for k in fold_results[0].metrics.keys() if k != "confusion_matrix"]
    mean_metrics = {}
    std_metrics = {}
    cv_coefficient = {}

    for key in metric_keys:
        values = [fr.metrics[key] for fr in fold_results]
        mean_val = float(np.mean(values))
        std_val = float(np.std(values))
        mean_metrics[key] = mean_val
        std_metrics[key] = std_val
        cv_coefficient[key] = std_val / mean_val if mean_val > 1e-8 else 0.0

    # Aggregate confusion matrices for emotion
    if config.task == "emotion" and "confusion_matrix" in fold_results[0].metrics:
        cm_sum = np.zeros_like(np.array(fold_results[0].metrics["confusion_matrix"]))
        for fr in fold_results:
            cm_sum += np.array(fr.metrics["confusion_matrix"])
        mean_metrics["confusion_matrix_agg"] = cm_sum.tolist()

    return ExperimentResult(
        config=config,
        fold_results=fold_results,
        mean_metrics=mean_metrics,
        std_metrics=std_metrics,
        cv_coefficient=cv_coefficient,
    )


def _run_taste_fold(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    sample_weights: Optional[np.ndarray],
    seed: int,
) -> Dict[str, float]:
    """Train and evaluate one fold for taste."""
    from sklearn.preprocessing import LabelEncoder

    le = LabelEncoder()
    y_train_cls = le.fit_transform(y_train.astype(int))

    # Map validation labels — handle unseen labels gracefully
    known_classes = set(le.classes_)
    y_val_int = y_val.astype(int)

    model = xgb.XGBClassifier(
        n_estimators=XGBOOST_N_ESTIMATORS,
        max_depth=XGBOOST_MAX_DEPTH,
        learning_rate=XGBOOST_LEARNING_RATE,
        random_state=seed,
        objective="multi:softmax",
        eval_metric="mlogloss",
        verbosity=0,
    )

    model.fit(X_train, y_train_cls, sample_weight=sample_weights)

    y_pred_cls = model.predict(X_val)
    y_pred = le.inverse_transform(y_pred_cls)

    return compute_metrics_taste(y_val_int, y_pred)


def _run_emotion_fold(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    sample_weights: Optional[np.ndarray],
    seed: int,
) -> Dict[str, float]:
    """Train and evaluate one fold for emotion."""
    n_classes = len(np.unique(np.concatenate([y_train, y_val])))

    # LogReg with class_weight if balancing is class_weight
    # (sample_weights are used for class_weight strategy,
    #  but LogReg supports class_weight='balanced' natively)
    if sample_weights is not None:
        model = LogisticRegression(
            solver="lbfgs",
            max_iter=2000,
            random_state=seed,
        )
        model.fit(X_train, y_train, sample_weight=sample_weights)
    else:
        model = LogisticRegression(
            solver="lbfgs",
            max_iter=2000,
            random_state=seed,
        )
        model.fit(X_train, y_train)

    y_pred = model.predict(X_val)
    y_proba = model.predict_proba(X_val)

    return compute_metrics_emotion(y_val, y_pred, y_proba, n_classes)


# =============================================================================
# WINNER SELECTION
# =============================================================================

def select_winner(results: List[ExperimentResult], task: str) -> ExperimentResult:
    """
    Select the best config using multi-criteria ranking.

    Taste priorities:
      1. MAE min (lower is better)
      2. Stability (std MAE low)
      3. Complexity penalty (fewer features preferred)

    Emotion priorities:
      1. Top-2 accuracy max
      2. Macro F1 max
      3. Stability (std top2 low)
      4. Complexity penalty
    """
    if task == "taste":
        # Sort: MAE ascending, then std ascending, then n_features ascending
        scored = []
        for r in results:
            mae = r.mean_metrics.get("mae", 999)
            mae_std = r.std_metrics.get("mae", 999)
            n_feat = r.config.n_features
            scored.append((mae, mae_std, n_feat, r))
        scored.sort(key=lambda x: (x[0], x[1], x[2]))
    else:
        # Sort: top2 descending, then F1 descending, then std ascending, then n_features ascending
        scored = []
        for r in results:
            top2 = r.mean_metrics.get("accuracy_top2", 0)
            f1 = r.mean_metrics.get("macro_f1", 0)
            top2_std = r.std_metrics.get("accuracy_top2", 999)
            n_feat = r.config.n_features
            scored.append((-top2, -f1, top2_std, n_feat, r))
        scored.sort(key=lambda x: (x[0], x[1], x[2], x[3]))

    return scored[0][-1]


# =============================================================================
# INSIGHT GENERATOR
# =============================================================================

def generate_insights(results: List[ExperimentResult], task: str) -> List[str]:
    """Generate rules-based textual insights from the results."""
    insights = []

    if len(results) < 2:
        return ["Not enough configs to generate comparative insights."]

    # Group results by balancing strategy
    by_balancing: Dict[str, List[ExperimentResult]] = {}
    for r in results:
        by_balancing.setdefault(r.config.balancing, []).append(r)

    # Group by block combo (ignoring kw_size and balancing)
    by_blocks: Dict[str, List[ExperimentResult]] = {}
    for r in results:
        key = "+".join(r.config.blocks)
        by_blocks.setdefault(key, []).append(r)

    primary_metric = "mae" if task == "taste" else "accuracy_top2"
    lower_is_better = task == "taste"

    # ---- Insight: KW impact ----
    kw_results = [r for r in results if "KW" in r.config.blocks]
    non_kw_results = [r for r in results if "KW" not in r.config.blocks]

    if kw_results and non_kw_results:
        best_kw = min(kw_results, key=lambda r: r.mean_metrics.get(primary_metric, 999)) if lower_is_better \
            else max(kw_results, key=lambda r: r.mean_metrics.get(primary_metric, 0))
        best_non_kw = min(non_kw_results, key=lambda r: r.mean_metrics.get(primary_metric, 999)) if lower_is_better \
            else max(non_kw_results, key=lambda r: r.mean_metrics.get(primary_metric, 0))

        kw_val = best_kw.mean_metrics[primary_metric]
        non_kw_val = best_non_kw.mean_metrics[primary_metric]

        if lower_is_better:
            if kw_val < non_kw_val * 0.98:
                insights.append(f"✅ KW features improve {primary_metric}: {kw_val:.3f} vs {non_kw_val:.3f}")
            elif kw_val > non_kw_val * 1.02:
                insights.append(f"⚠️ KW features DEGRADE {primary_metric}: {kw_val:.3f} vs {non_kw_val:.3f}")
            else:
                insights.append(f"➡️ KW features have negligible impact on {primary_metric}")
        else:
            if kw_val > non_kw_val * 1.02:
                insights.append(f"✅ KW features improve {primary_metric}: {kw_val:.3f} vs {non_kw_val:.3f}")
            elif kw_val < non_kw_val * 0.98:
                insights.append(f"⚠️ KW features DEGRADE {primary_metric}: {kw_val:.3f} vs {non_kw_val:.3f}")
            else:
                insights.append(f"➡️ KW features have negligible impact on {primary_metric}")

    # ---- Insight: KW size comparison ----
    kw_sizes_seen = sorted(set(r.config.kw_size for r in kw_results if r.config.kw_size > 0))
    if len(kw_sizes_seen) >= 2:
        for kw_sz in kw_sizes_seen:
            subset = [r for r in kw_results if r.config.kw_size == kw_sz]
            if subset:
                avg_cv = np.mean([r.cv_coefficient.get(primary_metric, 0) for r in subset])
                insights.append(f"  KW({kw_sz}): avg CV coefficient = {avg_cv:.3f}")
        # Stability comparison
        largest_kw = kw_sizes_seen[-1]
        smallest_kw = kw_sizes_seen[0]
        large_stds = [r.std_metrics.get(primary_metric, 0) for r in kw_results if r.config.kw_size == largest_kw]
        small_stds = [r.std_metrics.get(primary_metric, 0) for r in kw_results if r.config.kw_size == smallest_kw]
        if large_stds and small_stds:
            if np.mean(large_stds) > np.mean(small_stds) * 1.3:
                insights.append(f"⚠️ KW({largest_kw}) is less stable than KW({smallest_kw}) — consider smaller vocab")

    # ---- Insight: NEG block (taste only) ----
    if task == "taste":
        neg_results = [r for r in results if "NEG" in r.config.blocks]
        no_neg = [r for r in results if "NEG" not in r.config.blocks and "COS_POS" in r.config.blocks]
        if neg_results and no_neg:
            best_neg = min(neg_results, key=lambda r: r.mean_metrics.get("mae", 999))
            best_no_neg = min(no_neg, key=lambda r: r.mean_metrics.get("mae", 999))
            neg_w1 = best_neg.mean_metrics.get("within_1", 0)
            no_neg_w1 = best_no_neg.mean_metrics.get("within_1", 0)
            if neg_w1 > no_neg_w1 + 0.02:
                insights.append(f"✅ NEG block improves within±1: {neg_w1:.3f} vs {no_neg_w1:.3f}")
            else:
                insights.append(f"➡️ NEG block has marginal impact on within±1")

    # ---- Insight: META block ----
    meta_results = [r for r in results if "META" in r.config.blocks]
    no_meta = [r for r in results if "META" not in r.config.blocks]
    if meta_results and no_meta:
        best_meta_val = (min if lower_is_better else max)(
            [r.mean_metrics.get(primary_metric, 999 if lower_is_better else 0) for r in meta_results]
        )
        best_no_meta_val = (min if lower_is_better else max)(
            [r.mean_metrics.get(primary_metric, 999 if lower_is_better else 0) for r in no_meta]
        )
        threshold = 0.02
        if lower_is_better:
            if best_meta_val < best_no_meta_val - threshold:
                insights.append(f"✅ META block helps: {primary_metric} {best_meta_val:.3f} vs {best_no_meta_val:.3f}")
        else:
            if best_meta_val > best_no_meta_val + threshold:
                insights.append(f"✅ META block helps: {primary_metric} {best_meta_val:.3f} vs {best_no_meta_val:.3f}")

    # ---- Insight: Balancing ----
    if len(by_balancing) > 1:
        bal_summary = []
        for bal, res_list in by_balancing.items():
            avg = np.mean([r.mean_metrics.get(primary_metric, 0) for r in res_list])
            bal_summary.append((bal, avg))
        bal_summary.sort(key=lambda x: x[1], reverse=not lower_is_better)
        best_bal = bal_summary[0]
        insights.append(f"🏆 Best balancing strategy overall: '{best_bal[0]}' (avg {primary_metric}={best_bal[1]:.3f})")

    return insights


# =============================================================================
# REPORT WRITER
# =============================================================================

def write_report_json(
    results: List[ExperimentResult],
    winner: ExperimentResult,
    insights: List[str],
    task: str,
    metadata: dict,
    output_path: Path,
) -> Path:
    """Write JSON report."""
    report = {
        "metadata": metadata,
        "task": task,
        "gridlab_version": VERSION,
        "experiments": [],
        "winner": {
            "config_id": winner.config.config_id,
            "blocks": winner.config.blocks,
            "kw_size": winner.config.kw_size,
            "balancing": winner.config.balancing,
            "n_features": winner.config.n_features,
            "mean_metrics": winner.mean_metrics,
        },
        "insights": insights,
    }

    for r in results:
        exp = {
            "config_id": r.config.config_id,
            "blocks": r.config.blocks,
            "kw_size": r.config.kw_size,
            "balancing": r.config.balancing,
            "n_features": r.config.n_features,
            "mean_metrics": {k: v for k, v in r.mean_metrics.items() if k != "confusion_matrix_agg"},
            "std_metrics": r.std_metrics,
            "cv_coefficient": r.cv_coefficient,
            "folds": [{"fold": fr.fold, "metrics": {k: v for k, v in fr.metrics.items() if k != "confusion_matrix"}}
                      for fr in r.fold_results],
        }
        report["experiments"].append(exp)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gridlab_{task}_{timestamp}.json"
    filepath = output_path / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return filepath


def write_report_md(
    results: List[ExperimentResult],
    winner: ExperimentResult,
    insights: List[str],
    task: str,
    metadata: dict,
    output_path: Path,
) -> Path:
    """Write Markdown report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gridlab_{task}_{timestamp}.md"
    filepath = output_path / filename

    lines = []
    lines.append(f"# Grid Balancing Lab — {task.upper()}")
    lines.append(f"")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Seed:** {metadata.get('seed', '?')}  |  **CV folds:** {metadata.get('cv_folds', '?')}  |  **Samples:** {metadata.get('n_samples', '?')}")
    lines.append(f"")

    # Sort results for table
    if task == "taste":
        sorted_results = sorted(results, key=lambda r: r.mean_metrics.get("mae", 999))
    else:
        sorted_results = sorted(results, key=lambda r: -r.mean_metrics.get("accuracy_top2", 0))

    # ---- Main comparison table ----
    lines.append("## Results")
    lines.append("")

    if task == "taste":
        header = "| Rank | Config | Bal | Feats | MAE ↓ | RMSE | Exact Acc | ±1 | ±2 |"
        sep =    "|------|--------|-----|-------|-------|------|-----------|-----|-----|"
        lines.append(header)
        lines.append(sep)
        for i, r in enumerate(sorted_results, 1):
            m = r.mean_metrics
            is_winner = "🏆 " if r.config.config_id == winner.config.config_id else ""
            blocks_str = "+".join(r.config.blocks)
            if r.config.kw_size > 0:
                blocks_str += f"(KW{r.config.kw_size})"
            lines.append(
                f"| {i} | {is_winner}{blocks_str} | {r.config.balancing} | {r.config.n_features} | "
                f"**{m.get('mae', 0):.3f}** | {m.get('rmse', 0):.3f} | "
                f"{m.get('exact_accuracy', 0):.1%} | {m.get('within_1', 0):.1%} | {m.get('within_2', 0):.1%} |"
            )
    else:
        header = "| Rank | Config | Bal | Feats | Top-2 ↑ | Top-1 | Macro F1 |"
        sep =    "|------|--------|-----|-------|---------|-------|----------|"
        lines.append(header)
        lines.append(sep)
        for i, r in enumerate(sorted_results, 1):
            m = r.mean_metrics
            is_winner = "🏆 " if r.config.config_id == winner.config.config_id else ""
            blocks_str = "+".join(r.config.blocks)
            if r.config.kw_size > 0:
                blocks_str += f"(KW{r.config.kw_size})"
            lines.append(
                f"| {i} | {is_winner}{blocks_str} | {r.config.balancing} | {r.config.n_features} | "
                f"**{m.get('accuracy_top2', 0):.1%}** | {m.get('accuracy_top1', 0):.1%} | "
                f"{m.get('macro_f1', 0):.3f} |"
            )

    lines.append("")

    # ---- Stability section ----
    lines.append("## Stability")
    lines.append("")
    primary = "mae" if task == "taste" else "accuracy_top2"
    stab_header = "| Config | Bal | mean | std | CV coeff |"
    stab_sep =    "|--------|-----|------|-----|----------|"
    lines.append(stab_header)
    lines.append(stab_sep)

    for r in sorted_results:
        blocks_str = "+".join(r.config.blocks)
        if r.config.kw_size > 0:
            blocks_str += f"(KW{r.config.kw_size})"
        mean_val = r.mean_metrics.get(primary, 0)
        std_val = r.std_metrics.get(primary, 0)
        cv_val = r.cv_coefficient.get(primary, 0)
        flag = " ⚠️" if cv_val > 0.15 else ""
        lines.append(
            f"| {blocks_str} | {r.config.balancing} | {mean_val:.3f} | {std_val:.3f} | {cv_val:.3f}{flag} |"
        )

    lines.append("")

    # ---- Insights ----
    lines.append("## Insights")
    lines.append("")
    for insight in insights:
        lines.append(f"- {insight}")
    lines.append("")

    # ---- Recommendation ----
    lines.append("## Recommendation")
    lines.append("")
    w = winner
    lines.append(f"**Best config:** `{w.config.config_id}`")
    lines.append("")
    lines.append(f"| Parameter | Value |")
    lines.append(f"|-----------|-------|")
    lines.append(f"| Blocks | {', '.join(w.config.blocks)} |")
    lines.append(f"| KW size | {w.config.kw_size} |")
    lines.append(f"| Balancing | {w.config.balancing} |")
    lines.append(f"| # Features | {w.config.n_features} |")

    if task == "taste":
        lines.append(f"| MAE | {w.mean_metrics.get('mae', 0):.3f} ± {w.std_metrics.get('mae', 0):.3f} |")
        lines.append(f"| Within ±1 | {w.mean_metrics.get('within_1', 0):.1%} |")
    else:
        lines.append(f"| Top-2 Acc | {w.mean_metrics.get('accuracy_top2', 0):.1%} ± {w.std_metrics.get('accuracy_top2', 0):.3f} |")
        lines.append(f"| Macro F1 | {w.mean_metrics.get('macro_f1', 0):.3f} |")

    lines.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return filepath


# =============================================================================
# DRY-RUN PRINTER
# =============================================================================

def print_dry_run(configs: List[ExperimentConfig], task: str, metadata: dict) -> None:
    """Print the experiment plan without executing."""
    print(f"\n{'='*70}")
    print(f"  GRID BALANCING LAB — DRY RUN ({task.upper()})")
    print(f"{'='*70}")
    print(f"\n  Samples:  {metadata.get('n_samples', '?')}")
    print(f"  CV folds: {metadata.get('cv_folds', '?')}")
    print(f"  Seed:     {metadata.get('seed', '?')}")
    print(f"  Configs:  {len(configs)}")
    print()

    print(f"  {'#':>3}  {'Config ID':<55} {'Feats':>5}  {'Bal':<14}")
    print(f"  {'─'*3}  {'─'*55} {'─'*5}  {'─'*14}")

    for i, cfg in enumerate(configs, 1):
        print(f"  {i:>3}  {cfg.config_id:<55} {cfg.n_features:>5}  {cfg.balancing:<14}")

    print(f"\n  Total experiments: {len(configs)}")
    print(f"  Estimated folds:  {len(configs) * metadata.get('cv_folds', 5)}")
    print(f"{'='*70}\n")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Grid Balancing Lab — Ablation + Balancing Explorer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/gridlab.py --task taste --dry-run
  python tools/gridlab.py --task taste --cv 5 --seed 42 --output reports/
  python tools/gridlab.py --task emotion --balancing none,class_weight
  python tools/gridlab.py --task taste --kw-sizes 0,100,300 --balancing none,class_weight,undersample
        """,
    )

    parser.add_argument("--task", required=True, choices=["taste", "emotion"],
                        help="Task to run: taste or emotion")
    parser.add_argument("--kw-sizes", type=str, default="0,100,300",
                        help="Comma-separated keyword sizes (default: 0,100,300)")
    parser.add_argument("--balancing", type=str, default="none,class_weight,undersample",
                        help="Comma-separated balancing strategies (default: none,class_weight,undersample)")
    parser.add_argument("--cv", type=int, default=5,
                        help="Number of CV folds (default: 5)")
    parser.add_argument("--seed", type=int, default=XGBOOST_SEED,
                        help=f"Random seed (default: {XGBOOST_SEED})")
    parser.add_argument("--output", type=str, default="reports/",
                        help="Output directory for reports (default: reports/)")
    parser.add_argument("--max-configs", type=int, default=DEFAULT_MAX_CONFIGS,
                        help=f"Safety cap on max configs (default: {DEFAULT_MAX_CONFIGS})")
    parser.add_argument("--force", action="store_true",
                        help="Override the max-configs safety cap")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print experiment plan without executing")

    args = parser.parse_args()

    # Parse lists
    kw_sizes = [int(s.strip()) for s in args.kw_sizes.split(",")]
    balancing_strategies = [s.strip() for s in args.balancing.split(",")]

    # Validate balancing
    for bal in balancing_strategies:
        if bal not in VALID_BALANCING:
            parser.error(f"Invalid balancing strategy: '{bal}'. Valid: {VALID_BALANCING}")

    # Load dataset
    print(f"\n📊 Loading {args.task} dataset...")
    X_df, y_df, schema = load_dataset(args.task)
    y = y_df["label"].values

    print(f"  X shape: {X_df.shape}")
    print(f"  y shape: {y_df.shape}")

    # Class distribution
    classes, counts = np.unique(y, return_counts=True)
    print(f"  Classes: {len(classes)} | min count: {counts.min()} | max count: {counts.max()}")

    # Metadata
    metadata = {
        "task": args.task,
        "n_samples": len(y),
        "n_total_features": X_df.shape[1] - (1 if "tmdb_id" in X_df.columns else 0),
        "n_classes": len(classes),
        "class_distribution": {str(c): int(cnt) for c, cnt in zip(classes, counts)},
        "cv_folds": args.cv,
        "seed": args.seed,
        "kw_sizes": kw_sizes,
        "balancing_strategies": balancing_strategies,
        "keyword_vocab_size": len(schema.get("keyword_vocab", [])),
        "genre_vocab_size": len(schema.get("genre_vocab", [])),
        "gridlab_version": VERSION,
        "timestamp": datetime.now().isoformat(),
    }

    # Generate configs
    print(f"\n⚙️  Generating experiment configs...")
    configs = generate_configs(args.task, kw_sizes, balancing_strategies, X_df, schema)
    print(f"  Generated {len(configs)} configs")

    # Safety cap
    if len(configs) > args.max_configs and not args.force:
        print(f"\n❌ SAFETY CAP: {len(configs)} configs exceeds --max-configs={args.max_configs}")
        print(f"   Use --force to override, or reduce --kw-sizes / --balancing options.")
        sys.exit(1)

    # Dry run
    if args.dry_run:
        print_dry_run(configs, args.task, metadata)
        sys.exit(0)

    # Run experiments
    print(f"\n🚀 Running {len(configs)} experiments × {args.cv} folds...")
    results = []

    for i, config in enumerate(configs, 1):
        print(f"\n  [{i}/{len(configs)}] {config.config_id}")
        print(f"    blocks: {config.blocks} | kw: {config.kw_size} | bal: {config.balancing} | feats: {config.n_features}")

        result = run_experiment(X_df, y, config, args.cv, args.seed)

        # Print quick summary
        primary = "mae" if args.task == "taste" else "accuracy_top2"
        print(f"    → {primary}: {result.mean_metrics[primary]:.3f} ± {result.std_metrics[primary]:.3f}")

        results.append(result)

    # Select winner
    print(f"\n🏆 Selecting winner...")
    winner = select_winner(results, args.task)
    print(f"  Winner: {winner.config.config_id}")

    # Generate insights
    insights = generate_insights(results, args.task)

    # Write reports
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    json_path = write_report_json(results, winner, insights, args.task, metadata, output_path)
    md_path = write_report_md(results, winner, insights, args.task, metadata, output_path)

    print(f"\n📄 Reports written:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")

    # Final summary
    print(f"\n{'='*70}")
    print(f"  GRID BALANCING LAB — COMPLETE ({args.task.upper()})")
    print(f"{'='*70}")
    print(f"  Configs tested:  {len(configs)}")
    print(f"  Total folds:     {len(configs) * args.cv}")
    primary = "mae" if args.task == "taste" else "accuracy_top2"
    print(f"\n  🏆 Recommended: {winner.config.config_id}")
    print(f"     {primary}: {winner.mean_metrics[primary]:.3f} ± {winner.std_metrics[primary]:.3f}")
    print(f"     Features: {winner.config.n_features}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
