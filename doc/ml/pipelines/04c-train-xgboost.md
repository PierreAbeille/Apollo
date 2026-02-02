# Pipeline 04c: Train and Score XGBoost

> **Phase 3 de XGBoost** — Entraînement du modèle et scoring des candidats.

---

## 🎯 Objectif

Entraîner un classificateur XGBoost sur les données de Pipeline 04b, évaluer ses performances, puis scorer tous les candidats de Pipeline 04a pour les insérer dans `taste_candidates`.

---

## 📊 Vue d'Ensemble Rapide

**Input** :
- `data/train/X_train.parquet` : Features d'entraînement
- `data/train/y_train.parquet` : Labels
- `data/train/feature_schema.json` : Vocabulaires
- `data/cache/candidate_pool.json` : Films à scorer

**Output** :
- `models/xgb_taste_v{date}_{hash}.json` : Modèle sauvegardé
- Table `taste_candidates` : Recommandations avec scores

**Durée** : 1-5 minutes

**Fichier** : `apps/ml/pipelines/04c_train_and_score_xgboost.py`

---

## 🧠 Les 5 Étapes du Pipeline

### Étape 1 : Charger et Splitter les Données

```python
X_df = pd.read_parquet("data/train/X_train.parquet")
y_df = pd.read_parquet("data/train/y_train.parquet")

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=XGBOOST_TEST_SIZE,  # 0.2
    stratify=y,                    # Maintient le ratio de classes
    random_state=XGBOOST_SEED      # Reproductibilité
)
```

**Split stratifié** : Garantit que train et test ont le même ratio positifs/négatifs.

---

### Étape 2 : Entraîner XGBClassifier

```python
model = xgb.XGBClassifier(
    n_estimators=XGBOOST_N_ESTIMATORS,  # 100
    max_depth=XGBOOST_MAX_DEPTH,         # 6
    learning_rate=XGBOOST_LEARNING_RATE, # 0.1
    random_state=XGBOOST_SEED,
    use_label_encoder=False,
    eval_metric="logloss",
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=True  # Affiche la progression
)
```

**Hyperparamètres par défaut** :
- `n_estimators=100` : Nombre d'arbres de décision
- `max_depth=6` : Profondeur max de chaque arbre
- `learning_rate=0.1` : Vitesse d'apprentissage

---

### Étape 3 : Évaluer les Performances

```python
y_pred_proba = model.predict_proba(X_test)[:, 1]
y_pred = model.predict(X_test)

auc_roc = roc_auc_score(y_test, y_pred_proba)
auc_pr = average_precision_score(y_test, y_pred_proba)

print(f"AUC-ROC: {auc_roc:.4f}")
print(f"AUC-PR:  {auc_pr:.4f}")
print(classification_report(y_test, y_pred))
```

**Métriques clés** :

| Métrique | Description | Objectif |
|----------|-------------|----------|
| **AUC-ROC** | Capacité à distinguer positifs vs négatifs | > 0.7 |
| **AUC-PR** | Performance sur les positifs (classe minoritaire) | > 0.6 |
| **Precision** | % de prédictions positives correctes | > 0.7 |
| **Recall** | % de vrais positifs trouvés | > 0.6 |

---

### Étape 4 : Sauvegarder le Modèle

```python
model_version = f"xgb_taste_v{timestamp}_{config_hash}"
# Exemple: xgb_taste_v20260202_a1b2c3

model_path = f"models/{model_version}.json"
model.save_model(model_path)
```

**Format JSON** : Portable et lisible. Peut être rechargé avec :
```python
model = xgb.XGBClassifier()
model.load_model("models/xgb_taste_v20260202_a1b2c3.json")
```

---

### Étape 5 : Scorer les Candidats

```python
# Charger le pool de candidats
with open("data/cache/candidate_pool.json") as f:
    candidates = json.load(f)["candidates"]

# Scorer chaque candidat
scored = []
for tmdb_id in candidates:
    features = build_candidate_features(tmdb_id)  # Mêmes features que training
    proba = model.predict_proba(features.reshape(1, -1))[0, 1]
    scored.append((tmdb_id, float(proba)))

# Trier et sauvegarder
scored.sort(key=lambda x: x[1], reverse=True)
top_candidates = scored[:MAX_TASTE_CANDIDATES]

db.clear_taste_candidates()
db.insert_taste_candidates(top_candidates, model_version)
```

**Cohérence des features** : Le `feature_schema.json` garantit que les features sont construites exactement comme lors de l'entraînement.

---

## 📊 Interprétation des Scores

### Score XGBoost vs Score Cosinus

| Aspect | Cosinus (ancien) | XGBoost (nouveau) |
|--------|-----------------|-------------------|
| **Range** | [-1, 1] | [0, 1] |
| **Interprétation** | Similarité sémantique | Probabilité "tu vas aimer" |
| **Features** | Embeddings seuls | Embeddings + metadata |
| **Apprentissage** | Non supervisé | Supervisé (tes notes) |

---

### Feature Importances

Le pipeline affiche les 20 features les plus importantes :

```
📊 Top 20 Feature Importances:
  cosine_to_user_profile: 0.2847
  release_year_normalized: 0.0923
  genre_Science Fiction: 0.0612
  kw_dream: 0.0489
  genre_Thriller: 0.0401
  lang_en: 0.0387
  kw_heist: 0.0356
  ...
```

**Insights** :
- `cosine_to_user_profile` est probablement la plus importante (hérite du système existant)
- Certains genres/keywords peuvent être très discriminants pour tes goûts

---

## 🎬 Exemple d'Exécution

```bash
cd apps/ml
source .venv/bin/activate
python pipelines/04c_train_and_score_xgboost.py
```

**Logs attendus** :
```
======================================================================
Pipeline 04c: Train and Score XGBoost
======================================================================

🧠 Loading embeddings and computing user profile...
  Loaded 450 embeddings
  User profile norm: 0.9872

======================================================================
TRAINING PHASE
======================================================================

📊 Loading training data...
  X shape: (85, 332)
  y shape: (85, 2)
  Class distribution: {1: 45, 0: 40}

📖 Loading feature schema...
  Genres: 20
  Keywords: 300
  Languages: 10
  Total features: 332

🔀 Splitting data (80% train / 20% test)...
  Train: 68 samples
  Test: 17 samples

🚀 Training XGBClassifier...
  n_estimators: 100
  max_depth: 6
  learning_rate: 0.1

[0]	validation_0-logloss:0.65432
[50]	validation_0-logloss:0.34521
[99]	validation_0-logloss:0.29876

📈 Evaluating model...

  🎯 AUC-ROC: 0.8543
  🎯 AUC-PR:  0.8123

Classification Report:
              precision    recall  f1-score   support

    Negative       0.82      0.78      0.80         9
    Positive       0.80      0.84      0.82         8

    accuracy                           0.81        17

📊 Top 20 Feature Importances:
  cosine_to_user_profile: 0.2847
  release_year_normalized: 0.0923
  genre_Science Fiction: 0.0612
  ...

💾 Saved model to models/xgb_taste_v20260202_163000_a1b2c3.json

======================================================================
SCORING PHASE
======================================================================

📖 Loading candidate pool...
  Loaded 420 candidates

🔧 Building features and scoring...
  [100/420] Scored...
  [200/420] Scored...
  [420/420] Scored...

  Scored: 415
  Skipped (missing features): 5

💾 Inserting top 2000 candidates into taste_candidates...

🎬 TOP 10 RECOMMENDATIONS:
  1. Arrival (2016) - Score: 0.9234
  2. Blade Runner 2049 (2017) - Score: 0.8976
  3. Ex Machina (2014) - Score: 0.8812
  4. Annihilation (2018) - Score: 0.8654
  5. Tenet (2020) - Score: 0.8543
  6. Dune (2021) - Score: 0.8421
  7. Interstellar (2014) - Score: 0.8398
  8. The Matrix Resurrections (2021) - Score: 0.8267
  9. Moon (2009) - Score: 0.8145
  10. Looper (2012) - Score: 0.8023

======================================================================
SUMMARY
======================================================================
Training samples:     68
Test samples:         17
🎯 AUC-ROC:           0.8543
🎯 AUC-PR:            0.8123
Candidates scored:    415
Candidates saved:     415
Model version:        xgb_taste_v20260202_163000_a1b2c3
======================================================================
```

---

## 🔧 Arguments CLI

```bash
python pipelines/04c_train_and_score_xgboost.py [OPTIONS]

Options:
  --train-only    Entraîner sans scorer les candidats
  --score-only    Scorer avec le dernier modèle (sans réentraîner)
```

**Cas d'usage** :

```bash
# Entraînement complet + scoring
python pipelines/04c_train_and_score_xgboost.py

# Juste entraîner (ex: tester le modèle)
python pipelines/04c_train_and_score_xgboost.py --train-only

# Juste scorer (après avoir importé de nouveaux candidats)
python pipelines/04c_train_and_score_xgboost.py --score-only
```

---

## 🔧 Configuration

**Fichier** : `apps/ml/config/settings.py`

```python
# XGBoost hyperparameters
XGBOOST_SEED = 42
XGBOOST_TEST_SIZE = 0.2
XGBOOST_N_ESTIMATORS = 100
XGBOOST_MAX_DEPTH = 6
XGBOOST_LEARNING_RATE = 0.1

# Recommendations
MAX_TASTE_CANDIDATES = 2000
```

**Tuning XGBoost** :

| Paramètre | Défaut | Augmenter | Diminuer |
|-----------|--------|-----------|----------|
| `n_estimators` | 100 | Plus précis, risque overfitting | Plus rapide, moins précis |
| `max_depth` | 6 | Plus complexe | Plus simple, généralise mieux |
| `learning_rate` | 0.1 | Convergence rapide | Plus stable |

---

## 🐛 Dépannage

### Problème : AUC-ROC < 0.6 (mauvaises performances)

**Causes possibles** :
1. Pas assez de données d'entraînement
2. Features peu discriminantes
3. Labels mal calibrés

**Solutions** :
1. Noter plus de films (besoin 50+ samples)
2. Vérifier que `cosine_to_user_profile` est dans le top 5 importances
3. Ajuster `POSITIVE_RATING_THRESHOLD` et `NEGATIVE_RATING_THRESHOLD`

---

### Problème : Overfitting (train excellent, test mauvais)

**Symptôme** :
```
Train AUC: 0.99
Test AUC: 0.52
```

**Solutions** :
1. Diminuer `max_depth` (6 → 3)
2. Diminuer `n_estimators` (100 → 50)
3. Diminuer `TOP_KEYWORDS` (300 → 100)

---

### Problème : Candidats "skipped" élevé

**Cause** : Films sans `movie_features` en DB

**Solution** : Exécuter Pipeline 04a avec enrichissement ou Pipeline 02

---

## 📊 Comparaison avec Scoring Cosinus

Après avoir exécuté les deux systèmes, tu peux comparer :

```sql
-- Top 10 XGBoost
SELECT m.title, tc.taste_score, tc.model_version
FROM taste_candidates tc
JOIN movies m ON tc.tmdb_id = m.tmdb_id
WHERE tc.model_version LIKE 'xgb%'
ORDER BY tc.taste_score DESC
LIMIT 10;

-- Top 10 Cosinus (exécuter Pipeline 04 original séparément)
SELECT m.title, tc.taste_score, tc.model_version
FROM taste_candidates tc
JOIN movies m ON tc.tmdb_id = m.tmdb_id
WHERE tc.model_version LIKE 'MiniLM%'
ORDER BY tc.taste_score DESC
LIMIT 10;
```

---

## 📚 Ressources

- **[Pipeline 04a: Build Candidate Pool](04a-build-candidate-pool.md)**
- **[Pipeline 04b: Build Training Dataset](04b-build-training-dataset.md)**
- **[Pipeline 04: Build Candidates (version cosinus)](04-build-candidates.md)**

---

**Prochaines lectures** :
- [Pipeline Overview](../02-pipeline-overview.md)
- [Troubleshooting](../troubleshooting.md)
