# Exigences API Externes

Apollo dépend de trois services externes : **TMDb**, **Supabase**, et **HuggingFace**. Ce document détaille les prérequis pour chacun.

---

## 🎬 The Movie Database (TMDb)

**Site officiel** : [https://www.themoviedb.org](https://www.themoviedb.org)

### Obtenir une Clé API

1. Créer un compte sur TMDb
2. Aller dans [Settings → API](https://www.themoviedb.org/settings/api)
3. Demander une clé API (Developer)
4. Récupérer :
   - **API Key (v3)** : Pour requêtes REST classiques
   - **API Read Access Token (v4)** : Token Bearer pour authentification (recommandé)

### Configuration

**Web App** (`apps/web/.env.local`) :
```bash
TMDB_API_KEY=abc123xyz...
TMDB_API_READ_ACCESS_TOKEN=eyJhbGciOiJIUzI1NiJ9...
```

**ML Pipeline** (`apps/ml/.env.local`) :
```bash
TMDB_API_KEY=abc123xyz...
TMDB_API_READ_ACCESS_TOKEN=eyJhbGciOiJIUzI1NiJ9...
```

### Rate Limits

**Officiel** : 50 requêtes par seconde (TMDb API)

**Gestion Apollo** :
- **ML Pipeline** : Délai configurable via `TMDB_RATE_LIMIT_DELAY` (défaut: 1.5s → ~40 req/min)
- **Web App** : Batching par groupes de 10 (`hydrateWithTMDb`)

### Endpoints Utilisés

| Endpoint | Usage | Fréquence |
|----------|-------|-----------|
| `GET /movie/{id}` | Détails d'un film | Web: Fréquent, ML: Bulk |
| `GET /movie/{id}/similar` | Films similaires | ML: Pipeline 04 |
| `GET /movie/{id}?append_to_response=credits,keywords` | Métadonnées enrichies | ML: Pipeline 02 |
| `GET /search/movie` | Recherche par titre | ML: Pipeline 01 (import Letterboxd) |

### Langues

- **ML Pipeline** : Toujours `language=en-US` pour qualité sémantique
- **Web App** : `language=fr-FR` pour UX français, avec fallback `en-US` si synopsis vide

### Bonnes Pratiques

✅ **Faire** :
- Utiliser `append_to_response` pour combiner plusieurs appels en un seul
- Respecter les délais entre requêtes
- Gérer les erreurs 429 (Too Many Requests) avec retry exponentiel

❌ **Éviter** :
- Appels concurrents non contrôlés (saturation réseau)
- Requêtes répétées pour le même film (utiliser cache/DB)

---

## 🗄️ Supabase (PostgreSQL)

**Site officiel** : [https://supabase.com](https://supabase.com)

### Setup Initial

1. Créer un projet sur Supabase
2. Récupérer les credentials :
   - **Project URL** : `https://<project-id>.supabase.co`
   - **Publishable (anon) Key** : Clé publique pour API REST

### Configuration

**Web App** (`apps/web/.env.local`) :
```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**ML Pipeline** (`apps/ml/utils/database.py`) :
```python
# Configuration hardcodée ou via .env
DB_CONFIG = {
    "host": "db.your-project.supabase.co",
    "database": "postgres",
    "user": "postgres",
    "password": "your-db-password",
    "port": 5432
}
```

### Schéma de Base de Données

Créer les tables via SQL Editor de Supabase :

```sql
-- Voir doc/guidelines/data-contracts.md pour le schéma complet

CREATE TABLE movies (
    tmdb_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    release_year INTEGER,
    poster_path TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE movie_features (
    tmdb_id INTEGER PRIMARY KEY REFERENCES movies(tmdb_id),
    lang TEXT CHECK (lang IN ('en', 'fr')) NOT NULL DEFAULT 'en',
    overview TEXT,
    keywords JSONB DEFAULT '[]',
    genres JSONB DEFAULT '[]',
    "cast" JSONB DEFAULT '[]',
    crew JSONB DEFAULT '[]',
    text_for_embedding TEXT,
    tmdb_fetched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    tmdb_id INTEGER NOT NULL REFERENCES movies(tmdb_id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 10),
    is_done BOOLEAN DEFAULT FALSE,
    is_wishlisted BOOLEAN DEFAULT FALSE,
    is_recommended BOOLEAN DEFAULT FALSE,
    source TEXT CHECK (source IN ('letterboxd', 'app')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE taste_candidates (
    id SERIAL PRIMARY KEY,
    tmdb_id INTEGER NOT NULL REFERENCES movies(tmdb_id),
    taste_score FLOAT NOT NULL,
    model_version TEXT NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes pour performances
CREATE INDEX idx_movies_title ON movies(title);
CREATE INDEX idx_movie_features_tmdb ON movie_features(tmdb_id);
CREATE INDEX idx_interactions_tmdb ON interactions(tmdb_id);
CREATE INDEX idx_interactions_rating ON interactions(rating);
CREATE INDEX idx_taste_candidates_score ON taste_candidates(taste_score DESC);
```

### Row Level Security (RLS)

**État actuel** : Désactivé (mono-utilisateur)

**Future multi-utilisateur** :
```sql
ALTER TABLE interactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_interactions ON interactions
    FOR ALL
    USING (auth.uid() = user_id);
```

### Connexion ML Pipeline

Le pipeline utilise `psycopg2` directement (pas le client Supabase JS) :

```python
import psycopg2
from utils.database import get_connection

conn = get_connection()
cursor = conn.cursor()
cursor.execute("SELECT * FROM movies LIMIT 10")
```

**Driver requis** : `psycopg2-binary` (dans `requirements.txt`)

### Limites

**Tier Gratuit** :
- 500 MB stockage
- 50 MB fichiers (pas utilisé par Apollo)
- 2 GB de transfert/mois
- Connexions simultanées illimitées

**Recommandations** :
- Archiver les anciens `taste_candidates` si dépassement
- Éviter les `SELECT *` sur de grandes tables

---

## 🤗 HuggingFace (Sentence Transformers)

**Site officiel** : [https://huggingface.co](https://huggingface.co)

### Modèle Utilisé

**Nom** : `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

**Caractéristiques** :
- **Taille** : ~120 MB
- **Dimensions** : 384
- **Langues** : Multilingue (optimisé pour anglais)
- **License** : Apache 2.0

**Pourquoi ce modèle ?**
1. Équilibre performance/taille (léger)
2. Multilingue (mais meilleur en anglais → on utilise synopsis EN)
3. Pré-entraîné sur des tâches de similarité sémantique
4. Pas de GPU requis (CPU suffit)

### Installation

Le modèle est téléchargé automatiquement au premier lancement :

```bash
pip install sentence-transformers

# Premier run téléchargera le modèle dans ~/.cache/torch/hub/sentence_transformers/
python pipelines/03_build_embeddings.py
```

**Taille de téléchargement** : ~120 MB

### Configuration

**Pas de clé API requise** — Les modèles Sentence Transformers sont Open Source.

**Cache local** :
```
~/.cache/torch/hub/sentence_transformers/
├── paraphrase-multilingual-MiniLM-L12-v2/
│   ├── config.json
│   ├── pytorch_model.bin
│   ├── tokenizer_config.json
│   └── ...
```

### Usage Hors Ligne

Une fois téléchargé, le modèle fonctionne sans connexion internet :

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
# Pas de requête réseau après le premier téléchargement
```

### Alternatives (Future)

Si besoin de meilleures performances :

| Modèle | Dimensions | Taille | Performance |
|--------|-----------|--------|-------------|
| `all-MiniLM-L6-v2` | 384 | ~80 MB | Rapide, anglais uniquement |
| `all-mpnet-base-v2` | 768 | ~420 MB | Meilleure qualité, anglais |
| `paraphrase-multilingual-mpnet-base-v2` | 768 | ~970 MB | Top qualité, multilingue |

**Changement** : Modifier `EMBEDDING_MODEL` dans `apps/ml/config/settings.py`

---

## 🔐 Gestion Sécurisée des Secrets

### Variables d'Environnement

**❌ Ne jamais commit** :
- `.env.local`
- `.env`
- Fichiers contenant des clés

**✅ Utiliser** :
- `.env.example` (template vide pour référence)
- Gestionnaire de secrets (1Password, Bitwarden, etc.)

### Format Recommandé

**`.env.example`** :
```bash
# TMDb API
TMDB_API_KEY=
TMDB_API_READ_ACCESS_TOKEN=

# Supabase
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY=
```

**`.gitignore`** :
```
.env
.env.local
.env*.local
```

---

## 🧪 Test de Connectivité

### TMDb

```bash
# Test avec curl
curl "https://api.themoviedb.org/3/movie/550?api_key=YOUR_API_KEY"

# Doit retourner JSON avec titre "Fight Club"
```

### Supabase

```bash
# Test PostgreSQL
psql -h db.your-project.supabase.co -U postgres -d postgres -c "SELECT version();"

# Doit afficher la version PostgreSQL
```

### HuggingFace

```python
# Test download et encoding
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
embedding = model.encode("Test sentence")
print(f"Embedding dimensions: {len(embedding)}")  # Devrait afficher 384
```

---

## 📞 Support

### TMDb
- **Forum** : [https://www.themoviedb.org/talk](https://www.themoviedb.org/talk)
- **API Docs** : [https://developers.themoviedb.org/3](https://developers.themoviedb.org/3)

### Supabase
- **Discord** : [https://discord.supabase.com](https://discord.supabase.com)
- **Docs** : [https://supabase.com/docs](https://supabase.com/docs)

### HuggingFace
- **Forum** : [https://discuss.huggingface.co](https://discuss.huggingface.co)
- **Sentence Transformers Docs** : [https://www.sbert.net](https://www.sbert.net)

---

## ⚠️ Limitations Connues

1. **TMDb** : Pas de bulk endpoint (requêtes individuelles nécessaires)
2. **Supabase Gratuit** : 500 MB max (suffisant pour ~30k films avec features)
3. **Sentence Transformers** : CPU-only peut être lent sur gros volumes (>10k textes)

**Mitigation** :
- Batching et rate limiting pour TMDb
- Archivage périodique pour Supabase
- Cache embeddings en `.npy` pour éviter recalculs
