# Pipeline 04: Build Taste Candidates

> **Le "Cerveau" d'Apollo** — Génère tes recommandations personnalisées.

---

## 🎯 Objectif

Analyser tes goûts cinématographiques (films notés 8+), trouver des films similaires, et les scorer par pertinence sémantique pour créer une liste de 2000 recommandations classées.

---

## 📊 Vue d'Ensemble Rapide

**Input** :
- Table `interactions` (tes notes)
- Fichier `movie_embeddings.npy` (vecteurs sémantiques)
- API TMDb (films similaires)

**Output** :
- Table `taste_candidates` (Top 2000 films recommandés avec scores)

**Durée** : 10-20 minutes (dépend du nombre de films aimés)

**Fichier** : `apps/ml/pipelines/04_build_taste_candidates_full.py`

---

## 🧠 Les 5 Étapes du Pipeline

### Étape 1 : Analyse de Tes Goûts

**Code** :
```python
highly_rated = get_highly_rated_movies(interactions, MIN_RATING_FOR_SIMILAR)
# Récupère tous les films notés >= 8 (configurable)

print(f"Films aimés : {len(highly_rated)}")
# Exemple : Films aimés : 25
```

**Détails** :
- Filtre depuis la table `interactions`
- Seuls les films avec `rating >= MIN_RATING_FOR_SIMILAR` (défaut: 8)
- Ces films serviront de "graines" pour trouver des similaires

**Exemple** :
```
Films aimés :
- Inception (10/10)
- Interstellar (9/10)
- The Prestige (8/10)
- Donnie Darko (8/10)
→ 4 films vont servir à l'expansion
```

---

### Étape 2 : Calcul du Profil Utilisateur

**Code** :
```python
user_profile = calculate_user_profile(interactions, embeddings, tmdb_to_index)
# Moyenne pondérée des embeddings des films aimés

print(user_profile.shape)  # (384,)
```

**Formule** :
```
user_profile = Σ(rating_i × embedding_i) / Σ(rating_i)
```

**Exemple Concret** :
```python
# Films aimés avec leurs embeddings (simplifiés 3D pour clarté)
inception_emb = [0.8, -0.3, 0.5]      # Note: 10
interstellar_emb = [0.75, -0.25, 0.48]  # Note: 9
prestige_emb = [0.78, -0.28, 0.52]    # Note: 8

# Profil (moyenne pondérée)
user_profile = (10*inception + 9*interstellar + 8*prestige) / (10+9+8)
# Résultat : [0.778, -0.277, 0.5] (Le "toi idéal" en vecteur)
```

**💡 Pourquoi pondéré ?**
Tes films 10/10 "pèsent" plus lourd que tes 8/10 dans le profil.

---

### Étape 3 : Expansion des Candidats

**Code** :
```python
for film in highly_rated:
    similar = get_similar_movies(film.tmdb_id, language="en-US")
    candidates.extend(similar[:SIMILAR_MOVIES_PER_FILM])
    time.sleep(TMDB_RATE_LIMIT_DELAY)  # Rate limiting
```

**API Call** :
```
GET https://api.themoviedb.org/3/movie/27205/similar?language=en-US
→ Retourne 20 films similaires à Inception
```

**Résultat** :
```
Films sources : 4
Similar par film : 20
Total brut : 4 × 20 = 80 candidats
Uniques : ~50 (doublons retirés)
```

**Optimisation** :
- Détecte automatiquement les films déjà en DB (skip fetch metadata)
- Utilise `append_to_response` pour combiner plusieurs endpoints TMDb

---

### Étape 4 : Fetch & Encode Nouveaux Films

**Code** :
```python
# 4a: Identifier films manquants
missing = [film for film in candidates if film not in existing_features]

# 4b: Fetch TMDb metadata
for tmdb_id in missing:
    data = get_movie_details(tmdb_id, append_to_response="credits,keywords")
    # Construit text_for_embedding
    # Insert dans movie_features

# 4c: Générer embeddings
texts = [get_text_for_embedding(id) for id in missing]
new_embeddings = model.encode(texts, batch_size=32)
```

**Exemple de `text_for_embedding`** :
```
Genres: Science Fiction, Thriller. 
Keywords: dream, heist, subconscious. 
Cast: Leonardo DiCaprio, Marion Cotillard, Tom Hardy. 
Director: Christopher Nolan. 
Overview: A thief who steals corporate secrets through the use of dream-sharing...
```

**Résumé** : Seulement les films pas encore en DB sont traités (résumabilité).

---

### Étape 5 : Scoring & Sauvegarde

**Code** :
```python
scores = []
for candidate in all_candidates:
    if candidate.tmdb_id in already_rated:
        continue  # Skip films déjà vus
    
    emb = get_embedding(candidate.tmdb_id)
    score = cosine_similarity(user_profile, emb)
    scores.append((candidate.tmdb_id, float(score)))

# Trier par score décroissant
scores.sort(key=lambda x: x[1], reverse=True)

# Garder top 2000
top_candidates = scores[:MAX_TASTE_CANDIDATES]

# Sauvegarder
db.clear_taste_candidates()
db.insert_taste_candidates(top_candidates, model_version="MiniLM_v2")
```

**Exemple de résultats** :
```
Top 10 Recommandations :
1. Shutter Island (2010) - Score: 0.92
2. Memento (2000) - Score: 0.89
3. Arrival (2016) - Score: 0.87
4. Blade Runner 2049 (2017) - Score: 0.85
5. The Matrix (1999) - Score: 0.84
...
```

**Table finale** :
```sql
SELECT * FROM taste_candidates ORDER BY taste_score DESC LIMIT 5;

id | tmdb_id | taste_score | model_version       | generated_at
---+---------+-------------+--------------------+-------------
1  | 11324   | 0.92        | MiniLM_v2          | 2026-01-27
2  | 77     | 0.89        | MiniLM_v2          | 2026-01-27
...
```

---

## 🔧 Configuration

**Fichier** : `apps/ml/config/settings.py`

```python
# Seuil de note pour expansion
MIN_RATING_FOR_SIMILAR = 8  # Films >= 8 utilisés comme graines

# Candidats par film source
SIMILAR_MOVIES_PER_FILM = 20  # TMDb retourne 20 similaires

# Top N à sauvegarder
MAX_TASTE_CANDIDATES = 2000

# Rate limiting TMDb
TMDB_RATE_LIMIT_DELAY = 1.5  # Secondes entre requêtes (40/min)

# Modèle d'embedding
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
```

**Tuning** :

| Paramètre | Effet si augmenté | Effet si diminué |
|-----------|------------------|------------------|
| `MIN_RATING_FOR_SIMILAR` | Moins de films sources → Candidats plus ciblés | Plus de films sources → Plus de diversité |
| `SIMILAR_MOVIES_PER_FILM` | Plus de candidats → Plus de temps API | Moins de candidats → Plus rapide |
| `MAX_TASTE_CANDIDATES` | Plus de choix dans l'app web | Moins d'espace DB |

---

## 🎬 Exemple d'Exécution

```bash
cd apps/ml
source .venv/bin/activate
python pipelines/04_build_taste_candidates_full.py
```

**Logs attendus** :
```
======================================================================
Pipeline 04 [OPTIMIZED]: Personalized Recommendations
======================================================================
Loading existing embeddings from ./data/embeddings...
✓ Loaded 450 existing embeddings

Analyzing user interactions...
✓ Total interactions: 250
✓ Highly rated films (8+): 25

Calculating user profile (weighted average)...
✓ User profile: [0.678, -0.234, 0.523, ...]

Expanding candidate pool from 25 films...
  Processed 5/25 films...
  Processed 10/25 films...
  Processed 25/25 films...
✓ Found 487 unique candidate TMDB IDs

Checking which movies need TMDB data...
✓ All candidates already have features in database.

Generating embeddings for missing candidates...
✓ No missing embeddings to generate

Scoring recommendations...
✓ Scored 487 candidates

🎬 TOP 10 RECOMMENDATIONS:
  1. Shutter Island (2010) - Score: 0.921
  2. Memento (2000) - Score: 0.894
  3. Arrival (2016) - Score: 0.873
  4. Blade Runner 2049 (2017) - Score: 0.851
  5. The Matrix (1999) - Score: 0.842
  6. Tenet (2020) - Score: 0.837
  7. Ex Machina (2014) - Score: 0.829
  8. Looper (2012) - Score: 0.818
  9. Primer (2004) - Score: 0.804
  10. Predestination (2014) - Score: 0.798

======================================================================
SUMMARY
======================================================================
Films rated HIGHLY:        25
Candidates FOUND:          487
New movies FETCHED:        0
Candidates SCORED:         487
📡 TMDB API calls:         25
======================================================================
⏱ Duration: 11m 32s
```

---

## 🚀 Optimisations & Résumabilité

### Vérifications Smart

Le pipeline vérifie à chaque étape ce qui existe déjà :

```python
# 1. Features DB check
existing_features = db.fetch_all("SELECT tmdb_id FROM movie_features")
to_fetch = [id for id in candidates if id not in existing_features]

# 2. Embeddings cache check
to_encode = [id for id in candidates if id not in embeddings_index]

# 3. Skip films déjà notés
to_score = [id for id in candidates if id not in user_interactions]
```

**Résultat** : Si tu relances le pipeline après un crash, il ne refait PAS le travail déjà fait.

---

### Batch Processing

```python
# Au lieu de :
for film in films:
    embedding = model.encode(film.text)  # Lent

# On fait :
texts = [film.text for film in films]
embeddings = model.encode(texts, batch_size=32)  # 10× plus rapide
```

---

## 🐛 Dépannage

### Problème : "No highly rated movies found"

**Cause** : Aucun film >= 8 dans `interactions`.

**Solutions** :
1. Baisser `MIN_RATING_FOR_SIMILAR` à 7 ou 6
2. Vérifier import Letterboxd (Pipeline 01)

---

### Problème : Seulement 50 candidats (attendu : 2000)

**Cause** : Pool d'expansion trop petit.

**Solutions** :
1. Augmenter `SIMILAR_MOVIES_PER_FILM` (20 → 50)
2. Baisser `MIN_RATING_FOR_SIMILAR` (8 → 7)
3. Noter plus de films sur Letterboxd

---

### Problème : Scores tous bas (~0.3-0.5)

**Cause** : Profil utilisateur ou embeddings corrompus.

**Diagnostic** :
```python
# Vérifier profil
print(np.linalg.norm(user_profile))  # Doit être > 0

# Vérifier embeddings
emb = np.load('data/embeddings/movie_embeddings.npy')
print(np.isnan(emb).sum())  # Doit être 0
```

**Solution** : Régénérer embeddings (Pipeline 03)

---

## 📊 Métriques de Performance

| Métrique | Valeur Typique | Signification |
|----------|---------------|---------------|
| Films aimés | 20-50 | Sources d'expansion |
| Candidats uniques | 300-800 | Pool avant scoring |
| Nouveaux fetched | 0-100 | Films pas encore en DB |
| API calls | 20-100 | Dépend de l'expansion |
| Durée | 10-20 min | Première exécution |

---

## 🔄 Quand Relancer ?

### Toujours
- Après ajout de nouvelles notes Letterboxd (Pipeline 01)
- Si tes goûts ont évolué (nouvelles notes 8+)

### Rarement
- Refresh périodique (tous les 3-6 mois)
- Après changement de `MIN_RATING_FOR_SIMILAR`

---

## 📚 Ressources

- **[Concepts ML : Similarité Cosinus](../01-what-is-ml/.md#similarité-cosinus)**
- **[Pipeline Overview](../02-pipeline-overview.md)**
- **[Dépannage](../troubleshooting.md)**

---

**Prochaines lectures** :
- [Pipeline 01: Import Letterboxd](01-import-letterboxd.md)
- [Pipeline 03: Build Embeddings](03-build-embeddings.md)
