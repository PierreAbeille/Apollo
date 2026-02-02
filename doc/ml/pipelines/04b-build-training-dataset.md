# Pipeline 04b: Build Training Dataset

> **Phase 2 de XGBoost** — Construction des features et labels pour l'entraînement.

---

## 🎯 Objectif

Construire un dataset d'entraînement (X, y) à partir des films notés par l'utilisateur, en utilisant les métadonnées TMDb et les embeddings pour créer des features discriminantes.

---

## 📊 Vue d'Ensemble Rapide

**Input** :
- Table `interactions` (labels depuis rating)
- Table `movie_features` (lang, genres, keywords)
- Fichier `movie_embeddings.npy` (pour centroid similarity)

**Output** :
- `data/train/X_train.parquet` : Features
- `data/train/y_train.parquet` : Labels
- `data/train/feature_schema.json` : Vocabulaires pour scoring
- `models/<timestamp>_pos_centroids.npy` : Centroïdes sauvegardés

**Durée** : < 1 minute

**Fichier** : `apps/ml/pipelines/04b_build_training_dataset.py`

---

## 🏷️ Règles de Labeling (V1)

### Labels binaires

```python
def get_label(interaction):
    if not interaction["is_done"]:
        return None  # Non vu, ignorer
    
    rating = interaction.get("rating")
    if rating is None:
        return None  # Vu mais pas noté
    
    if rating >= 8:
        return 1  # Positif (tu as aimé)
    elif rating <= 5:
        return 0  # Négatif (tu n'as pas aimé)
    else:
        return None  # 6-7 = ambigu, ignorer
```

**Mapping** :

| Rating | Label | Interprétation |
|--------|-------|----------------|
| 8, 9, 10 | `y=1` | Positif (aimé) |
| 6, 7 | Ignoré | Ambigu |
| 1, 2, 3, 4, 5 | `y=0` | Négatif (pas aimé) |
| Non noté | Ignoré | Pas de signal |

**Pourquoi ignorer 6-7 ?**
Ces notes sont ambiguës — ni vraiment aimé, ni vraiment détesté. Les inclure ajouterait du bruit au modèle.

---

## 📐 Features V2 (Multi-Centroïdes)

### Vue d'ensemble

| Groupe | Feature | Dimension | Description |
|--------|---------|-----------|-------------|
| Centroïdes | `cos_pos_c0..c4` | 5 | Cosinus vers chaque centroïde positif |
| Centroïdes | `max_cos_pos` | 1 | Maximum sur les 5 centroïdes |
| Metadata | `release_year_normalized` | 1 | Année normalisée |
| Language | `lang_*` | 10 | One-hot top 10 langues |
| Genres | `genre_*` | 20 | Multi-hot top 20 genres |
| Keywords | `kw_*` | 300 | Multi-hot top 300 keywords |

**Total** : ~337 features

---

### Feature 1-6 : Multi-Centroïdes (KMeans)

Au lieu d'une simple moyenne (user_profile), on capture la diversité des goûts via K centroïdes.

```python
# 1. Extraire embeddings des films positifs (rating >= 8)
positive_embeddings = embeddings[positive_indices]

# 2. KMeans clustering (K=5)
kmeans = KMeans(n_clusters=5, random_state=42)
kmeans.fit(positive_embeddings)
centroids = kmeans.cluster_centers_  # Shape: (5, 384)

# 3. Pour chaque film, calculer cosinus vers chaque centroïde
for i, centroid in enumerate(centroids):
    cos_pos_ci = cosine_similarity(movie_emb, centroid)

# 4. Ajouter max_cos_pos pour capture rapide
max_cos_pos = max(cos_pos_c0, cos_pos_c1, ..., cos_pos_c4)
```

**Avantage** : Capture les goûts variés (ex: sci-fi ET comédie romantique)

---

### Feature 2 : Release Year (Normalized)

```python
release_year = movie.get("release_year") or 2000
normalized_year = (release_year - 2000) / 50
# 1950 → -1.0
# 2000 → 0.0
# 2025 → 0.5
```

**Intuition** : Certains utilisateurs préfèrent les films récents, d'autres les classiques.

---

### Feature 3 : Language One-Hot

Encodage one-hot des 10 langues les plus fréquentes.

```python
lang_vocab = ["en", "fr", "es", "de", "ja", "ko", "it", "zh", "pt", "ru"]

# Pour un film en anglais
lang_encoded = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]

# Pour un film en japonais
lang_encoded = [0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
```

---

### Feature 4 : Genres Multi-Hot

Encodage multi-hot des 20 genres les plus fréquents.

```python
genre_vocab = [
    "Drama", "Comedy", "Thriller", "Action", "Romance",
    "Horror", "Science Fiction", "Crime", "Mystery", "Adventure",
    ...
]

# Pour Inception (Science Fiction, Action, Thriller)
genres_encoded = [0, 0, 1, 1, 0, 0, 1, 0, 0, 0, ...]
```

---

### Feature 5 : Keywords Multi-Hot

Encodage multi-hot des 300 keywords les plus fréquents.

```python
keyword_vocab = [
    "based on novel", "dystopia", "love", "murder", "revenge",
    "heist", "dream", "friendship", "time travel", "robot",
    ...
]

# Pour Inception (dream, heist, subconscious)
keywords_encoded = [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, ...]
```

**Pourquoi 300 ?**
- Trop peu → On rate des signaux importants
- Trop (1000+) → Overfitting sur un petit dataset

---

## 📁 Format de Sortie

### X_train.parquet

```
       cosine_to_user_profile  release_year_normalized  lang_en  lang_fr  ... kw_heist  kw_dream
0                       0.87                     0.20      1.0      0.0  ...      1.0       1.0
1                       0.45                    -0.40      1.0      0.0  ...      0.0       0.0
2                       0.72                     0.10      0.0      1.0  ...      0.0       0.0
...
```

### y_train.parquet

```
   label  tmdb_id
0      1    27205
1      0    12345
2      1   157336
...
```

### feature_schema.json

```json
{
  "feature_order": [
    "cosine_to_user_profile",
    "release_year_normalized",
    "lang_en", "lang_fr", ...
    "genre_Drama", "genre_Comedy", ...
    "kw_based on novel", "kw_dystopia", ...
  ],
  "genre_vocab": ["Drama", "Comedy", ...],
  "keyword_vocab": ["based on novel", ...],
  "lang_vocab": ["en", "fr", ...],
  "positive_threshold": 8,
  "negative_threshold": 5
}
```

**Usage** : Ce fichier est utilisé par Pipeline 04c pour reconstruire les mêmes features lors du scoring.

---

## 🎬 Exemple d'Exécution

```bash
cd apps/ml
source .venv/bin/activate
python pipelines/04b_build_training_dataset.py
```

**Logs attendus** :
```
======================================================================
Pipeline 04b: Build Training Dataset
======================================================================

📊 Loading embeddings from data/embeddings...
  Loaded 450 embeddings (384 dims)

📖 Loading interactions...
  Found 250 total interactions

🧠 Computing user profile...
  Profile computed (norm: 0.9872)

📊 Loading movie features...
  Found 450 movies with features

📖 Building feature vocabularies...
  Genres: 20 (from 28 total)
  Keywords: 300 (from 1847 total)
  Languages: 10 (from 15 total)

🔧 Building training samples...

  X shape: (85, 332)
  y shape: (85, 2)
  Feature count: 332

💾 Saved X_train to data/train/X_train.parquet
💾 Saved y_train to data/train/y_train.parquet
💾 Saved feature schema to data/train/feature_schema.json

======================================================================
SUMMARY
======================================================================
Total interactions:        250
✓ Positive samples (y=1):  45
✓ Negative samples (y=0):  40
⚠ Ignored (6-7 ratings):   65
✗ Missing features:        100

Class balance: 52.9% positive
======================================================================
```

---

## 🔧 Configuration

**Fichier** : `apps/ml/config/settings.py`

```python
# Feature dimensions
TOP_GENRES = 20
TOP_KEYWORDS = 300
TOP_LANGUAGES = 10

# Labeling thresholds
POSITIVE_RATING_THRESHOLD = 8  # rating >= 8 → y=1
NEGATIVE_RATING_THRESHOLD = 5  # rating <= 5 → y=0
```

**Tuning** :

| Paramètre | Augmenter | Diminuer |
|-----------|-----------|----------|
| `TOP_KEYWORDS` | Plus de signaux, risque overfitting | Moins de features, généralise mieux |
| `POSITIVE_RATING_THRESHOLD` | Moins de positifs, plus sélectif | Plus de positifs |
| `NEGATIVE_RATING_THRESHOLD` | Plus de négatifs | Moins de négatifs |

---

## 📊 Statistiques à Surveiller

### Équilibre des classes

**Idéal** : 40-60% de positifs

```
Class balance: 52.9% positive → ✓ OK

Class balance: 85% positive → ⚠ Déséquilibré
→ Solution: Baisser POSITIVE_RATING_THRESHOLD
```

### Nombre de samples

**Minimum recommandé** : 50+ pour un modèle stable

```
Positive: 45, Negative: 40 → Total: 85 ✓ OK

Positive: 10, Negative: 8 → Total: 18 ⚠ Trop peu
→ Solution: Noter plus de films ou ajuster thresholds
```

---

## 🐛 Dépannage

### Problème : "Missing features: X" élevé

**Cause** : Films sans `movie_features` en DB

**Solutions** :
1. Exécuter Pipeline 02 (`02_sync_tmdb_features.py`)
2. Exécuter Pipeline 04a avec enrichissement activé

---

### Problème : Class balance très déséquilibré (> 80%)

**Cause** : Seuils de labeling mal calibrés

**Solutions** :
1. Ajuster `POSITIVE_RATING_THRESHOLD` ou `NEGATIVE_RATING_THRESHOLD`
2. Utiliser class weights dans XGBoost (Pipeline 04c)

---

### Problème : Pas assez de samples (< 30)

**Cause** : Pas assez de films notés avec signal clair

**Solutions** :
1. Noter plus de films sur Letterboxd
2. Élargir les seuils (7+ positif, 6- négatif)

---

## 📚 Ressources

- **[Pipeline 04a: Build Candidate Pool](04a-build-candidate-pool.md)**
- **[Pipeline 04c: Train XGBoost](04c-train-xgboost.md)**
- **[Concepts ML: Embeddings](../01-what-is-ml.md)**

---

**Prochaines lectures** :
- [Pipeline 04c: Train and Score XGBoost](04c-train-xgboost.md)
- [Pipeline Overview](../02-pipeline-overview.md)
