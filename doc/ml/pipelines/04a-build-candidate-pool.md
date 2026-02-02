# Pipeline 04a: Build Candidate Pool

> **Phase 1 de XGBoost** — Expansion TMDb Similar pour constituer le pool de candidats.

---

## 🎯 Objectif

Extraire les films similaires depuis TMDb pour chaque film que tu as noté 8+ (seeds), et sauvegarder ce pool dans un fichier JSON pour les étapes suivantes.

---

## 📊 Vue d'Ensemble Rapide

**Input** :
- Table `interactions` (films notés 8+)
- API TMDb (Similar Movies endpoint)

**Output** :
- Fichier `data/cache/candidate_pool.json`
- Table `movie_features` (nouveaux films enrichis)

**Durée** : 5-15 minutes (dépend du nombre de seeds)

**Fichier** : `apps/ml/pipelines/04a_build_candidate_pool.py`

---

## 🧠 Les 4 Étapes du Pipeline

### Étape 1 : Charger les Seeds

```python
interactions = db.get_all_interactions()
highly_rated = get_highly_rated_movies(interactions, MIN_RATING_FOR_SIMILAR)
# Films avec rating >= 8
```

**Exemple** :
```
Films seeds (8+) : 25
- Inception (10)
- Interstellar (9)
- The Prestige (8)
- ...
```

---

### Étape 2 : Expansion TMDb Similar

Pour chaque seed, on appelle l'API TMDb Similar :

```python
for tmdb_id in highly_rated:
    similar = get_similar_movies(tmdb_id, language="en-US", page=1)
    candidates.update([m["id"] for m in similar["results"][:20]])
    time.sleep(TMDB_RATE_LIMIT_DELAY)  # Rate limiting
```

**API Call** :
```
GET https://api.themoviedb.org/3/movie/27205/similar
→ Retourne 20 films similaires à Inception
```

**Résultat** :
```
Seeds : 25
Similar par seed : 20
Total brut : 500
Uniques après dédoublonnage : ~400
```

---

### Étape 3 : Enrichir les Nouveaux Films

Les films candidats qui n'ont pas encore de `movie_features` sont enrichis via TMDb :

```python
for tmdb_id in candidates_without_features:
    data = get_movie_details(tmdb_id, append_to_response="credits,keywords")
    
    db.upsert_movie(tmdb_id, title, year, poster_path)
    db.upsert_movie_features(
        tmdb_id=tmdb_id,
        lang="en",
        genres=genres,
        keywords=keywords,
        text_for_embedding=text
    )
```

**Optimisation** : `append_to_response` combine 3 endpoints en 1 seul appel.

---

### Étape 4 : Sauvegarder le Pool

```python
# Exclure les films déjà notés par l'utilisateur
final_candidates = list(candidate_ids - rated_ids)

output = {
    "candidates": final_candidates,
    "count": len(final_candidates),
    "min_rating_threshold": MIN_RATING_FOR_SIMILAR,
    "similar_per_film": SIMILAR_MOVIES_PER_FILM,
}

with open("data/cache/candidate_pool.json", "w") as f:
    json.dump(output, f, indent=2)
```

---

## 📁 Format de Sortie

**Fichier** : `data/cache/candidate_pool.json`

```json
{
  "candidates": [27205, 157336, 603, 11324, ...],
  "count": 487,
  "min_rating_threshold": 8,
  "similar_per_film": 20
}
```

**Contenu** :
- `candidates` : Liste des tmdb_id candidats (films à scorer)
- `count` : Nombre total
- `min_rating_threshold` : Seuil utilisé pour les seeds
- `similar_per_film` : Nombre de similaires par seed

---

## 🎬 Exemple d'Exécution

```bash
cd apps/ml
source .venv/bin/activate
python pipelines/04a_build_candidate_pool.py
```

**Logs attendus** :
```
======================================================================
Pipeline 04a: Build Candidate Pool
======================================================================

📖 Loading user interactions...
  Found 180 rated films, 250 total interactions
  Found 25 films rated >= 8

🎯 Expanding candidate pool from 25 seed films...
  [5/25] Processed... (85 candidates so far)
  [10/25] Processed... (165 candidates so far)
  [25/25] Processed... (487 candidates so far)
✓ Found 487 unique candidate TMDb IDs

📊 Discovery pool: 420 movies (excluding rated films)

Checking which movies need TMDB data...
🔄 Fetching metadata for 45 movies from TMDB...
  [10/45] Arrival... saved.
  [20/45] Blade Runner 2049... saved.
  [45/45] Annihilation... saved.

💾 Saved 420 candidates to data/cache/candidate_pool.json

======================================================================
SUMMARY
======================================================================
Seed films (rated >= 8): 25
Similar movies fetched:   487
Unique candidates:        487
New movies processed:     45
📡 TMDB API calls:        70
======================================================================
```

---

## 🔧 Configuration

**Fichier** : `apps/ml/config/settings.py`

```python
# Seuil pour les seeds
MIN_RATING_FOR_SIMILAR = 8  # Films >= 8 utilisés

# Nombre de similaires par seed
SIMILAR_MOVIES_PER_FILM = 20

# Rate limiting TMDb
TMDB_RATE_LIMIT_DELAY = 1.5  # Secondes entre requêtes
```

**Tuning** :

| Paramètre | Augmenter | Diminuer |
|-----------|-----------|----------|
| `MIN_RATING_FOR_SIMILAR` | Moins de seeds, plus ciblé | Plus de seeds, plus de diversité |
| `SIMILAR_MOVIES_PER_FILM` | Plus de candidats par seed | Plus rapide |

---

## 🐛 Dépannage

### Problème : "No highly rated movies"

**Cause** : Aucun film >= 8 dans `interactions`

**Solutions** :
1. Baisser `MIN_RATING_FOR_SIMILAR` à 7 ou 6
2. Vérifier que Pipeline 01 a été exécuté

---

### Problème : Pool trop petit (< 100 candidats)

**Cause** : Peu de seeds ou films avec peu de similaires TMDb

**Solutions** :
1. Baisser `MIN_RATING_FOR_SIMILAR`
2. Augmenter `SIMILAR_MOVIES_PER_FILM`
3. Noter plus de films sur Letterboxd

---

### Problème : Rate limit TMDb (429 error)

**Solution** : Augmenter `TMDB_RATE_LIMIT_DELAY` à 2.0

---

## 🔄 Résumabilité

Le pipeline est **partiellement résumable** :
- Les seeds sont toujours recalculés
- Les films déjà en `movie_features` sont skippés
- Le fichier `candidate_pool.json` est écrasé à chaque exécution

---

## 📚 Ressources

- **[Pipeline Overview](../02-pipeline-overview.md)**
- **[Pipeline 04b: Build Training Dataset](04b-build-training-dataset.md)**
- **[Pipeline 04c: Train XGBoost](04c-train-xgboost.md)**

---

**Prochaines lectures** :
- [Pipeline 04b: Build Training Dataset](04b-build-training-dataset.md)
- [Pipeline 04: Build Candidates (version cosinus)](04-build-candidates.md)
