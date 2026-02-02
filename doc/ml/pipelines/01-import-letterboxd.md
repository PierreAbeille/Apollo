# Pipeline 01: Import Letterboxd

> **Point d'entrée des données** — Importe tes films depuis Letterboxd vers Apollo.

---

## 🎯 Objectif

Parser le fichier CSV exporté de Letterboxd, matcher chaque film avec son ID TMDb, et insérer les données dans les tables `movies` et `interactions`.

---

## 📊 Vue d'Ensemble Rapide

**Input** :
- Fichier CSV Letterboxd (`letterboxd-data.csv` ou `ml_dataset_full.csv`)
- Clé API TMDb

**Output** :
- Table `movies` : Films avec tmdb_id, titre, année, poster
- Table `interactions` : Notes, statuts (watched, wishlist)

**Durée** : 2-5 minutes (dépend du nombre de films)

**Fichier** : `apps/ml/pipelines/01_import_letterboxd.py`

---

## 🔀 Deux Formats Supportés

### Format Ancien (letterboxd-data.csv)

```csv
title,release_date,rating,is_wishlisted,is_recommended
"Inception",2010,10,False,False
"Interstellar",2014,9,False,False
```

**Usage** :
```bash
python pipelines/01_import_letterboxd.py
```

---

### Format Nouveau (ml_dataset_full.csv)

```csv
item_id,title,year,interaction,watched_date,watchlist_added_date,rating,liked,rewatch,review_text,tags,diary_entry_id
1234,Inception,2010,watched,2024-01-15,,4.5,True,False,"Amazing!","scifi,thriller",5678
```

**Usage** :
```bash
python pipelines/01_import_letterboxd.py --new-format
```

**Différences clés** :

| Aspect | Format Ancien | Format Nouveau |
|--------|--------------|----------------|
| Année | `release_date` | `year` |
| Note | 1-10 | 1-5 (×2 conversion) |
| Statut | `is_wishlisted` | `interaction` (watched/watchlist) |
| Enrichi | Non | Oui (liked, rewatch, review_text) |

---

## 🧠 Logique de Conversion

### Notes (Rating)

Le format nouveau utilise l'échelle Letterboxd (1-5 étoiles).

```python
# Conversion automatique
if use_new_format:
    rating_db = letterboxd_rating * 2  # 4.5 → 9
else:
    rating_db = rating  # Déjà 1-10
```

**Mapping** :

| Letterboxd | DB (1-10) |
|------------|-----------|
| ★★★★★ (5) | 10 |
| ★★★★½ (4.5) | 9 |
| ★★★★ (4) | 8 |
| ★★★½ (3.5) | 7 |
| ★★★ (3) | 6 |
| etc. | etc. |

---

### Statuts (is_done, is_wishlisted)

```python
if use_new_format:
    interaction_type = row.get("interaction", "").lower()
    is_done = interaction_type == "watched"
    is_wishlisted = interaction_type == "watchlist"
else:
    is_done = True  # Implicite
    is_wishlisted = row.get("is_wishlisted") == "True"
```

---

## 🔧 Arguments CLI

```bash
python pipelines/01_import_letterboxd.py [OPTIONS]

Options:
  --new-format    Utilise le format ml_dataset_full.csv
  --csv PATH      Chemin personnalisé vers le CSV
```

**Exemples** :

```bash
# Format ancien
python pipelines/01_import_letterboxd.py

# Format nouveau
python pipelines/01_import_letterboxd.py --new-format

# CSV personnalisé
python pipelines/01_import_letterboxd.py --csv ~/Downloads/export.csv
```

---

## 📋 Processus de Matching TMDb

### Étape 1 : Normalisation du titre

```python
title_normalized = normalize_title(title)
# "The Matrix (1999)" → "matrix"
# "Le Fabuleux Destin d'Amélie Poulain" → "fabuleux destin amelie poulain"
```

### Étape 2 : Recherche API

```
GET https://api.themoviedb.org/3/search/movie?query=inception&year=2010
```

### Étape 3 : Match scoring

```python
# Algorithme de sélection :
1. Si 1 seul résultat → Accepté
2. Si plusieurs résultats → Comparer années
3. Si années différentes → Log "ambiguous"
4. Si aucun résultat → Log "unmatched"
```

### Étape 4 : Cache SQLite

```python
# Cache local pour éviter requêtes répétées
cache.set(title, year, tmdb_id)
# Prochaine exécution : cache.get(title, year) → tmdb_id direct
```

---

## 📊 Logs et Diagnostics

### Fichiers de log

| Fichier | Contenu |
|---------|---------|
| `data/logs/unmatched.csv` | Films non trouvés sur TMDb |
| `data/logs/ambiguous.csv` | Films avec plusieurs correspondances |

### Format unmatched.csv

```csv
title,year,reason
"Un Film Obscur",2015,"No TMDb results"
"Titre Mal Écrit",2020,"No TMDb results"
```

### Exemple de console

```
======================================================================
Pipeline 01: Import Letterboxd
======================================================================
Using CSV: data/raw/letterboxd/ml_dataset_full.csv
Format: NEW (ml_dataset_full.csv)

Processing 250 entries...
  [50/250] Inception (2010) → tmdb_id: 27205 ✓
  [100/250] Interstellar (2014) → tmdb_id: 157336 ✓
  [150/250] Unknown Film (2015) → ✗ No match
  ...

======================================================================
SUMMARY
======================================================================
✓ Imported: 248/250
✗ Unmatched: 2
⚠ Ambiguous: 0
📡 TMDb API calls: 175 (cache hits: 75)
======================================================================
```

---

## 🐛 Dépannage

### Problème : "No TMDb results" pour un film connu

**Causes possibles** :
1. Typo dans le titre CSV
2. Année incorrecte
3. Film pas encore sur TMDb

**Solutions** :
1. Vérifier orthographe dans CSV
2. Chercher manuellement sur [themoviedb.org](https://www.themoviedb.org)
3. Corriger le CSV et relancer

---

### Problème : Mauvais tmdb_id (film différent)

**Cause** : Titre générique ou année incorrecte

**Solution** :
1. Supprimer l'entrée du cache :
   ```bash
   python -c "from utils.cache import TMDBCache; c = TMDBCache('data/cache/tmdb_match.db'); c.delete('Titre Film', 2020)"
   ```
2. Corriger l'année dans le CSV
3. Relancer le pipeline

---

### Problème : Rate limit TMDb (429 error)

**Cause** : Trop de requêtes (> 40/min)

**Solution** : Augmenter le délai dans `settings.py`
```python
TMDB_RATE_LIMIT_DELAY = 2.0  # Défaut: 1.5
```

---

## 🔄 Idempotence

Le pipeline est **idempotent** : tu peux le relancer sans créer de doublons.

```python
# Upsert (INSERT ON CONFLICT)
db.upsert_movie(tmdb_id, title, year, poster_path)
db.upsert_interaction(tmdb_id, rating, is_done, is_wishlisted, source="letterboxd")
```

**Comportement** :
- Film déjà en DB → Mise à jour (si nouvelles données)
- Film absent → Insertion
- Note changée → Mise à jour

---

## 📚 Ressources

- **[Pipeline Overview](../02-pipeline-overview.md)**
- **[Data Contracts](../../guidelines/data-contracts.md)**
- **[Troubleshooting](../troubleshooting.md)**

---

**Prochaines lectures** :
- [Pipeline 02: Sync TMDb Features](02-sync-tmdb-features.md)
- [Pipeline 04: Build Candidates](04-build-candidates.md)
