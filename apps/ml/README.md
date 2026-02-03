# Apollo ML Pipeline 🎬🤖

Ce module gère le moteur de recommandation personnalisé d'Apollo. Il transforme tes données Letterboxd en suggestions intelligentes basées sur des embeddings sémantiques et/ou un modèle XGBoost.

## 🚀 Quick Start

### Option A: Recommandations par Cosinus (classique)

```bash
source .venv/bin/activate
python pipelines/04_build_taste_candidates_full.py
```

### Option B: Recommandations par XGBoost ML (nouveau)

```bash
source .venv/bin/activate

# 1. Importer les données (avec nouveau format CSV)
python pipelines/01_import_letterboxd.py --new-format

# 2. Synchroniser les features TMDb (inchangé)
python pipelines/02_sync_tmdb_features.py

# 3. Générer les embeddings (inchangé)
python pipelines/03_build_embeddings.py

# 4a. Construire le pool de candidats
python pipelines/04a_build_candidate_pool.py

# 4b. Construire le dataset d'entraînement
python pipelines/04b_build_training_dataset.py

# 4c. Entraîner XGBoost et scorer les candidats
python pipelines/04c_train_and_score_xgboost.py
```

## 🏗️ Architecture des Pipelines

### Pipelines de base (1-3)

| Pipeline | Description |
|----------|-------------|
| `01_import_letterboxd.py` | Importe le CSV Letterboxd. Supporte `--new-format` pour `ml_dataset_full.csv` |
| `02_sync_tmdb_features.py` | Récupère les métadonnées TMDb (synopsis, cast, genres, keywords) |
| `03_build_embeddings.py` | Génère les embeddings avec `paraphrase-multilingual-MiniLM-L12-v2` |

### Pipeline 04 - Recommandations

**Version Cosinus (originale)** :
- `04_build_taste_candidates_full.py` : Score par similarité cosinus au profil utilisateur

**Version XGBoost ML (nouvelle)** :
| Pipeline | Description |
|----------|-------------|
| `04a_build_candidate_pool.py` | Expansion via TMDb Similar, sauvegarde dans `candidate_pool.json` |
| `04b_build_training_dataset.py` | Construit X/y pour XGBoost (features V1: cosine, year, lang, genres, keywords) |
| `04c_train_and_score_xgboost.py` | Entraîne, évalue (AUC/PR-AUC), et score les candidats |

### Pipeline 05 - Système de Vibes (Mood Scores)

| Pipeline | Description |
|----------|-------------|
| `05_build_mood_scores.py` | Calcule les scores mood↔film pour **tous les films avec embedding** |

#### Concept

Le système de "Vibes" permet de filtrer les films par **atmosphère** plutôt que par genre. Contrairement aux genres (Action, Comédie...), les vibes décrivent une **sensation** cross-genre.

#### Les 9 Vibes

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

#### Algorithme

1. **Encodage des vibes** : Chaque description de vibe → embedding 384D
2. **Similarité cosinus** : Score = `cosine_similarity(movie_embedding, vibe_embedding)`
3. **Stockage** : Table `movie_mood_scores(tmdb_id, mood_id, similarity_score)`

#### Affichage (Frontend)

Le score brut (0-1) est converti en note `/10` où **10/10 = 60%+ de similarité** :
```
score_display = min(10, round((similarity_score / 0.6) * 10))
```

#### Configuration (`config/moods.py`)

Les vibes sont définies dans `MOODS` avec un `id`, `name`, et `description` servant à l'embedding.

## ⚙️ Configuration (`config/settings.py`)

### Recommandations
- `MIN_RATING_FOR_SIMILAR` (défaut: 8) : Seuil pour les films "seeds"
- `MAX_TASTE_CANDIDATES` (défaut: 2000) : Nombre max de recommandations

### XGBoost
- `XGBOOST_N_ESTIMATORS` (défaut: 100) : Nombre d'arbres
- `XGBOOST_MAX_DEPTH` (défaut: 6) : Profondeur max des arbres
- `XGBOOST_LEARNING_RATE` (défaut: 0.1) : Taux d'apprentissage

### Labels
- `POSITIVE_RATING_THRESHOLD` (défaut: 8) : rating >= 8 → y=1
- `NEGATIVE_RATING_THRESHOLD` (défaut: 5) : rating <= 5 → y=0

## 🗂️ Structure du projet

```
apps/ml/
├── clients/         # DB (Supabase) et TMDb API
├── config/          # settings.py
├── embeddings/      # Encoder et similarité
├── features/        # Text builder et profil utilisateur
├── pipelines/       # Scripts d'exécution
├── data/
│   ├── cache/       # candidate_pool.json
│   ├── embeddings/  # movie_embeddings.npy
│   ├── train/       # X_train.parquet, y_train.parquet
│   └── raw/         # CSV Letterboxd
└── models/          # Modèles XGBoost sauvegardés
```

## 💡 Notes Techniques

- **Langue** : Données TMDb en anglais pour l'IA
- **Résilience** : Tous les pipelines sont "resumables"
- **Base de données** : Utilisation d'`upsert` (ON CONFLICT) pour éviter les doublons
- **XGBoost** : Le modèle est sauvegardé en JSON pour reproductibilité

