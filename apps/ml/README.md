# Apollo ML Pipeline 🎬🤖

Ce module gère le moteur de recommandation personnalisé d'Apollo. Il transforme tes données Letterboxd en suggestions intelligentes basées sur des embeddings sémantiques.

## 🚀 Quick Start (Générer des recommandations)

Si tu as déjà ajouté de nouveaux films sur Letterboxd ou si tu veux juste rafraîchir tes suggestions :

1. **Active l'environnement** : `source .venv/bin/activate` (depuis `apps/ml`)
2. **Lance le pipeline complet** :
   ```bash
   python pipelines/04_build_taste_candidates_full.py
   ```
   *Ce script s'occupe de tout : trouver des candidats sur TMDB, les importer, les enrichir, générer les vecteurs et les scorer.*

## 🏗️ Architecture des Pipelines

Le système est découpé en 4 étapes logiques :

1.  **`01_import_letterboxd.py`** : Importe ton fichier `letterboxd-data.csv`. Il matche les titres avec TMDB et les stocke dans Supabase.
2.  **`02_sync_tmdb_features.py`** : Récupère les métadonnées riches (synopsis, cast, genres, etc.) en anglais pour optimiser la qualité des vecteurs.
3.  **`03_build_embeddings.py`** : Transforme les textes en vecteurs numériques (384 dimensions) via le modèle `paraphrase-multilingual-MiniLM-L12-v2`.
4.  **`04_build_taste_candidates_full.py`** (Le "Cerveau") : 
    *   Analyse tes goûts (films notés 8+).
    *   Demande à TMDB des films similaires.
    *   Score les candidats par similarité cosinus avec ton "Profil utilisateur".
    *   Sauvegarde les meilleurs résultats dans la table `taste_candidates`.

## ⚙️ Configuration (`config/settings.py`)

- `MIN_RATING_FOR_SIMILAR` (défaut: 8) : Seuil de note pour qu'un film serve de base à l'expansion des candidats.
- `TMDB_RATE_LIMIT_DELAY` (défaut: 1.5) : Délai de sécurité pour respecter les quotas de TMDB (50 req/min).
- `MAX_TASTE_CANDIDATES` (défaut: 2000) : Nombre de recommandations à conserver en base.

## 🗂️ Structure du projet

- `clients/` : Wrappers pour Supabase (Postgres) et TMDB API.
- `embeddings/` : Logique de vectorisation et de calcul de similarité.
- `features/` : Construction du "Text for Embedding" et calcul du profil utilisateur.
- `data/` : Cache local et embeddings sauvegardés (pour éviter de tout recalculer).

## 💡 Notes Techniques
- **Langue** : Les données TMDB sont récupérées en **anglais** pour l'IA (meilleure sémantique), mais l'application web peut afficher ce qu'elle veut.
- **Résilience** : Le pipeline 04 est "resumable". Si tu l'arrêtes, il vérifiera ce qui est déjà en base au redémarrage pour ne pas gâcher de requêtes API.
- **Base de données** : Toutes les écritures utilisent des `upsert` (ON CONFLICT) pour garantir qu'il n'y a jamais de doublons.
