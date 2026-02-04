# Apollo ML Pipeline 🎬🤖

Ce module gère le moteur de recommandation personnalisé d'Apollo. Il transforme tes données Letterboxd en suggestions intelligentes basées sur des embeddings sémantiques et un modèle XGBoost.

## 🚀 Quick Start

```bash
source .venv/bin/activate

# 1. Importer les données Letterboxd
python pipelines/01_import_letterboxd.py --new-format

# 2. Synchroniser les features TMDb
python pipelines/02_sync_tmdb_features.py

# 3. Générer les embeddings
python pipelines/03_build_embeddings.py

# 4a. Construire le pool de candidats
python pipelines/04a_build_candidate_pool.py

# 4b. Construire le dataset d'entraînement (avec anti-centroid V1.5)
python pipelines/04b_build_training_dataset.py

# 4c. Entraîner XGBoost et scorer avec MMR
python pipelines/04c_train_and_score_xgboost.py

# 5. (Optionnel) Générer les scores par vibe
python pipelines/05_build_mood_scores.py
```

## 🏗️ Architecture des Pipelines

### Pipelines de base (1-3)

| Pipeline | Description |
|----------|-------------|
| `01_import_letterboxd.py` | Importe le CSV Letterboxd. Supporte `--new-format` pour `ml_dataset_full.csv` |
| `02_sync_tmdb_features.py` | Récupère les métadonnées TMDb (synopsis, cast, genres, keywords) |
| `03_build_embeddings.py` | Génère les embeddings avec `paraphrase-multilingual-MiniLM-L12-v2` |

### Pipeline 04 - Recommandations XGBoost (V1.5)

| Pipeline | Description |
|----------|-------------|
| `04a_build_candidate_pool.py` | Expansion via TMDb Similar, sauvegarde dans `candidate_pool.json` |
| `04b_build_training_dataset.py` | Construit X/y avec features V1.5 (centroids positifs + **anti-centroid**) |
| `04c_train_and_score_xgboost.py` | Entraîne, évalue, et score avec **MMR reranking** |

### Pipeline 05 - Système de Vibes

| Pipeline | Description |
|----------|-------------|
| `05_build_mood_scores.py` | Calcule les scores mood↔film pour tous les films avec embedding |

---

## ✨ Nouveautés V1.5

### 1. Features Distance aux Négatifs

Le modèle apprend maintenant à **éviter** les films similaires à ceux que tu as détestés.

| Feature | Description |
|---------|-------------|
| `min_cos_pos` | Similarité minimum aux 5 centroids positifs |
| `mean_cos_pos` | Similarité moyenne aux centroids positifs |
| `cos_to_neg_center` | Similarité à l'**anti-centroid** (films ≤4/10) |
| `pos_neg_margin` | `max_cos_pos - cos_to_neg_center` (marge de sécurité) |

**Fichier** : `features/centroid_features.py`

### 2. MMR Reranking (Diversité)

Après le scoring XGBoost, un reranking **Maximal Marginal Relevance** évite un top-10 trop homogène.

```
MMR(film) = λ × Score - (1-λ) × max(Similarité aux déjà sélectionnés)
```

Par défaut : `λ = 0.7` (70% pertinence, 30% diversité)

**Fichier** : `features/mmr_reranker.py`

---

## 🧠 Système de Vibes (Moods)

### Concept

Le système de "Vibes" filtre les films par **atmosphère** plutôt que par genre. Les vibes décrivent une **sensation** cross-genre.

### Les 9 Vibes

| ID | Nom FR | Description |
|----|--------|-------------|
| `mind_bending` | Retourne le cerveau | Puzzles mentaux, twists (*Inception, Matrix*) |
| `feel_good` | Ça fait du bien | Réconfortant, optimiste (*Intouchables, Amélie*) |
| `dark_gritty` | Sombre & Réaliste | Viscéral, brut (*Joker, Se7en*) |
| `tension` | Tension pure | Adrénaline, stress (*Mad Max, Whiplash*) |
| `surreal` | Onirique & Étrange | Surréaliste, poétique (*Spirited Away*) |
| `epic` | Grand Spectacle | Épique, grandiose (*Dune, Gladiator*) |
| `intimate` | Intimiste & Calme | Contemplatif (*Lost in Translation*) |
| `nostalgia` | Nostalgie | Rétro, mélancolie douce (*Stranger Things*) |
| `disturbing` | Dérangeant & Viscéral | Malaise, provocant (*Midsommar*) |

### Affichage (Frontend)

Score brut (0-1) → note `/10` où **10/10 = 60%+ de similarité** :
```
score_display = min(10, round((similarity_score / 0.6) * 10))
```

---

## ⚙️ Configuration (`config/settings.py`)

### Recommandations
| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `MAX_TASTE_CANDIDATES` | 2000 | Nombre max de recommandations |
| `MIN_RATING_FOR_SIMILAR` | 8 | Seuil pour les films "seeds" |

### XGBoost
| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `XGBOOST_N_ESTIMATORS` | 100 | Nombre d'arbres |
| `XGBOOST_MAX_DEPTH` | 6 | Profondeur max |
| `XGBOOST_LEARNING_RATE` | 0.1 | Taux d'apprentissage |

### Seuils de labeling
| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `POSITIVE_RATING_THRESHOLD` | 9 | rating >= 9 → positif pour centroids |
| `NEGATIVE_RATING_THRESHOLD` | 5 | rating <= 5 → négatif (exclus du training) |
| `ANTI_CENTROID_THRESHOLD` | 4 | rating <= 4 → utilisé pour anti-centroid |

### MMR (V1.5)
| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `MMR_ENABLED` | True | Activer le reranking |
| `MMR_LAMBDA` | 0.7 | 0=diversité pure, 1=pertinence pure |
| `MMR_TOP_K` | 200 | Nombre de candidats à reranker |

---

## 🗂️ Structure du projet

```
apps/ml/
├── clients/           # DB (Supabase) et TMDb API
├── config/            # settings.py, moods.py
├── embeddings/        # Encoder et similarité
├── features/
│   ├── centroid_features.py  # V1.5: Positif + Négatif
│   ├── mmr_reranker.py       # V1.5: Diversité
│   └── preference_score.py   # Profil utilisateur
├── pipelines/         # Scripts d'exécution
├── data/
│   ├── cache/         # candidate_pool.json
│   ├── embeddings/    # movie_embeddings.npy
│   ├── train/         # X_train.parquet, y_train.parquet, feature_schema.json
│   └── raw/           # CSV Letterboxd
└── models/            # Modèles XGBoost + centroids (.npy)
```

---

## 💡 Notes Techniques

- **Langue** : Données TMDb en anglais pour l'IA
- **Résilience** : Tous les pipelines sont "resumables"
- **Base de données** : Utilisation d'`upsert` (ON CONFLICT) pour éviter les doublons
- **XGBoost** : Modèle sauvegardé en JSON + centroids en `.npy`
- **Anti-centroid** : Nécessite au moins 3-5 films notés ≤4 pour être calculé


