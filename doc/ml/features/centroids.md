# Multi-Centroïdes : Représentation des Goûts Utilisateur

> **Évolution V2** — Remplacement de `user_profile` (moyenne) par KMeans clustering.

---

## 🎯 Pourquoi Multi-Centroïdes ?

### Problème avec la moyenne simple

L'approche V1 calculait un seul vecteur "profil utilisateur" comme moyenne pondérée des embeddings des films aimés :

```python
user_profile = Σ(rating_i × embedding_i) / Σ(rating_i)
```

**Limitation** : Si tu aimes à la fois les films de science-fiction ET les comédies romantiques, la moyenne crée un vecteur "au milieu" qui ne représente ni l'un ni l'autre.

```
Sci-Fi ●                    ● Comédie Romantique
         \                 /
          \               /
           ● user_profile (moyenne)
                ↓
        Ne ressemble à rien !
```

---

### Solution : Multi-Centroïdes (KMeans)

On utilise KMeans pour identifier K=5 clusters dans tes goûts :

```
Sci-Fi ●──────● Centroïde 0 (Sci-Fi cluster)

Comédie ●─────● Centroïde 1 (Comédie cluster)

Thriller ●────● Centroïde 2 (Thriller cluster)
```

**Avantage** : Chaque centroïde capture un "pôle" de tes goûts.

---

## 📐 Features Générées

Pour chaque film, on calcule 6 features :

| Feature | Range | Description |
|---------|-------|-------------|
| `cos_pos_c0` | [-1, 1] | Cosinus vers centroïde 0 |
| `cos_pos_c1` | [-1, 1] | Cosinus vers centroïde 1 |
| `cos_pos_c2` | [-1, 1] | Cosinus vers centroïde 2 |
| `cos_pos_c3` | [-1, 1] | Cosinus vers centroïde 3 |
| `cos_pos_c4` | [-1, 1] | Cosinus vers centroïde 4 |
| `max_cos_pos` | [-1, 1] | Maximum des 5 cosinus |

**Interprétation** :
- `cos_pos_c0 = 0.92` → Le film est très proche du cluster 0 (ex: Sci-Fi)
- `max_cos_pos = 0.92` → Le film correspond bien à AU MOINS un de tes goûts

---

## 🧠 Algorithme

### Pipeline 04b : Calcul des Centroïdes

```python
from features.centroid_features import compute_positive_centroids

# 1. Identifier les films positifs (rating >= 8)
positive_tmdb_ids = [
    i["tmdb_id"] for i in interactions 
    if i["is_done"] and i["rating"] >= 8
]

# 2. Calculer les centroïdes
centroids, _ = compute_positive_centroids(
    embeddings=embeddings,           # (N, 384) numpy array
    positive_tmdb_ids=positive_ids,  # List[int]
    tmdb_to_index=mapping,           # Dict[int, int]
    n_clusters=5,                    # K clusters
    random_state=42                  # Reproductibilité
)

# 3. Sauvegarder
save_centroids(centroids, "centroids_v20260202", models_dir)
```

### Pipeline 04b/04c : Calcul des Features

```python
from features.centroid_features import compute_centroid_features

# Pour un film
movie_emb = embeddings[tmdb_to_index[tmdb_id]]  # (384,)
features = compute_centroid_features(movie_emb, centroids)
# → [cos_c0, cos_c1, cos_c2, cos_c3, cos_c4, max_cos]
```

---

## 📁 Fichiers Produits

### Centroïdes

```
models/centroids_v{timestamp}_pos_centroids.npy
```

Format : NumPy array `(5, 384)` — 5 centroïdes de dimension 384.

### Feature Schema

```json
{
  "feature_order": [
    "cos_pos_c0", "cos_pos_c1", "cos_pos_c2", 
    "cos_pos_c3", "cos_pos_c4", "max_cos_pos",
    "release_year_normalized",
    ...
  ],
  "n_clusters": 5,
  "centroids_version": "centroids_v20260202_161800",
  ...
}
```

---

## 🔧 Configuration

**Fichier** : `features/centroid_features.py`

```python
DEFAULT_N_CLUSTERS = 5      # Nombre de clusters
DEFAULT_RANDOM_STATE = 42   # Seed pour reproductibilité
```

**Tuning** :

| K | Effet |
|---|-------|
| K=3 | Moins de granularité, généralise plus |
| K=5 | Bon compromis (défaut) |
| K=10 | Plus de clusters, risque d'overfitting si peu de positifs |

**Règle** : K doit être ≤ nombre de films positifs.

---

## 📊 Exemple Concret

### Données d'entrée

Films aimés (rating ≥ 8) :
- Inception (Sci-Fi/Thriller)
- Interstellar (Sci-Fi/Drama)
- The Notebook (Romance/Drama)
- La La Land (Romance/Musical)
- Parasite (Thriller/Drama)

### Centroïdes résultants

| Centroïde | Films dominants | Genres capturés |
|-----------|-----------------|-----------------|
| C0 | Inception, Interstellar | Sci-Fi |
| C1 | The Notebook, La La Land | Romance |
| C2 | Parasite, Inception | Thriller |
| C3-C4 | (variants mixtes) | Drama |

### Features pour un nouveau film

**Blade Runner 2049** (Sci-Fi/Thriller) :
```
cos_pos_c0: 0.89  ← Proche du cluster Sci-Fi
cos_pos_c1: 0.23  ← Éloigné du cluster Romance
cos_pos_c2: 0.67  ← Moyennement proche Thriller
cos_pos_c3: 0.45
cos_pos_c4: 0.38
max_cos_pos: 0.89 ← Bon candidat !
```

**The Proposal** (Romance/Comedy) :
```
cos_pos_c0: 0.15  ← Éloigné Sci-Fi
cos_pos_c1: 0.72  ← Proche Romance !
cos_pos_c2: 0.21
cos_pos_c3: 0.34
cos_pos_c4: 0.28
max_cos_pos: 0.72 ← Candidat potentiel
```

---

## 🔄 Gestion des Cas Limites

### Moins de K positifs

Si tu as seulement 3 films aimés mais K=5 demandé :

```python
# Comportement automatique
if len(positive_ids) < n_clusters:
    actual_clusters = len(positive_ids)  # Utilise 3
    # Padding avec zéros pour les colonnes manquantes
```

**Logs** :
```
⚠ Only 3 positives, using 3 clusters instead of 5
```

### Film sans embedding

Si un film candidat n'a pas d'embedding :

```python
if tmdb_id not in tmdb_to_index:
    centroid_feats = np.zeros(n_clusters + 1)  # Tous à 0
```

---

## 🧪 Tests

**Fichier** : `features/centroid_features.py`

```bash
cd apps/ml
python features/centroid_features.py
```

**Output** :
```
🧪 Running centroid features tests...

✓ test_compute_positive_centroids passed
✓ test_compute_centroid_features passed
✓ test_compute_centroid_features_batch passed
✓ test_feature_names passed
✓ test_fewer_positives_than_clusters passed

✅ All tests passed!
```

---

## 📚 API Reference

### `compute_positive_centroids()`

```python
def compute_positive_centroids(
    embeddings: np.ndarray,           # (N, D) full embedding matrix
    positive_tmdb_ids: List[int],     # TMDb IDs of liked movies
    tmdb_to_index: Dict[int, int],    # Mapping TMDb ID → index
    n_clusters: int = 5,              # Number of clusters
    random_state: int = 42            # Random seed
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Returns:
        centroids: (n_clusters, D) centroid vectors
        positive_embeddings: (n_positives, D) embeddings used
    """
```

### `compute_centroid_features()`

```python
def compute_centroid_features(
    movie_embedding: np.ndarray,  # (D,) single embedding
    centroids: np.ndarray         # (K, D) centroids
) -> np.ndarray:
    """
    Returns:
        features: (K+1,) array [cos_c0, ..., cos_cK-1, max_cos]
    """
```

### `save_centroids()` / `load_centroids()`

```python
def save_centroids(centroids, model_version, models_dir) -> str:
    """Saves to {models_dir}/{model_version}_pos_centroids.npy"""

def load_centroids(model_version, models_dir) -> np.ndarray:
    """Loads from {models_dir}/{model_version}_pos_centroids.npy"""
```

---

## 📚 Ressources

- **[Pipeline 04b: Build Training Dataset](04b-build-training-dataset.md)**
- **[Pipeline 04c: Train XGBoost](04c-train-xgboost.md)**
- **[Concepts ML: Embeddings](../01-what-is-ml.md)**

---

**Prochaines lectures** :
- [Pipeline Overview](../02-pipeline-overview.md)
- [Troubleshooting](../troubleshooting.md)
