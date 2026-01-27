# Dépannage ML Pipeline

> **Guide de résolution des problèmes courants** lors de l'exécution des pipelines ML Apollo.

---

## 🚨 Erreurs TMDb API

### Erreur : `429 Too Many Requests`

**Message complet** :
```
requests.exceptions.HTTPError: 429 Client Error: Too Many Requests
```

**Cause** : Tu as dépassé la limite de 50 requêtes/seconde de TMDb.

**Solutions** :

#### Solution 1 : Augmenter le délai
```python
# Éditer apps/ml/config/settings.py
TMDB_RATE_LIMIT_DELAY = 2.0  # Au lieu de 1.5
```

#### Solution 2 : Vérifier les appels en double
```bash
# Lancer avec verbose logging
python pipelines/02_sync_tmdb_features.py

# Chercher des requêtes répétées pour le même film
```

#### Solution 3 : Attendre et réessayer
```bash
# Si c'est un ban temporaire de TMDb (rare), attendre 5-10 minutes
sleep 600 && python pipelines/02_sync_tmdb_features.py
```

---

### Erreur : `401 Unauthorized`

**Cause** : Clé API TMDb invalide ou expirée.

**Solutions** :

```bash
# Vérifier que .env.local existe
ls apps/ml/.env.local

# Vérifier le contenu
cat apps/ml/.env.local
# Doit contenir : TMDB_API_KEY=abc123xyz...

# Tester la clé avec curl
curl "https://api.themoviedb.org/3/movie/550?api_key=YOUR_API_KEY"
# Doit retourner JSON, pas d'erreur
```

**Si clé invalide** :
1. Aller sur [TMDb Settings → API](https://www.themoviedb.org/settings/api)
2. Régénérer une nouvelle clé
3. Mettre à jour `.env.local`

---

### Erreur : `404 Not Found` (Film Spécifique)

**Cause** : Le film n'existe pas dans TMDb ou ID incorrect.

**Solution** :
```python
# Vérifier manuellement
# Aller sur https://www.themoviedb.org/movie/{tmdb_id}

# Si film inexistant, skip (normal pour 1-2% des cas)
# Pipeline 01 devrait avoir trouvé le bon ID, mais parfois TMDb supprime des entrées
```

---

## 🗄️ Erreurs Base de Données

### Erreur : `relation "movies" does not exist`

**Cause** : Les tables PostgreSQL n'ont pas été créées.

**Solution** :
```bash
# Se connecter à Supabase
psql -h db.your-project.supabase.co -U postgres -d postgres

# Exécuter le schéma
\i path/to/schema.sql

# Ou copier-coller le SQL depuis doc/guidelines/data-contracts.md
```

**Vérifier que les tables existent** :
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';

-- Doit afficher : movies, movie_features, interactions, taste_candidates
```

---

### Erreur : `connection refused`

**Cause** : Credentials Supabase incorrects ou VPN/firewall bloque.

**Solutions** :

#### Vérifier credentials
```python
# Éditer apps/ml/utils/database.py
DB_CONFIG = {
    "host": "db.xxx.supabase.co",  # Vérifier l'URL
    "database": "postgres",
    "user": "postgres",
    "password": "YOUR_PASSWORD",   # Vérifier le mot de passe
    "port": 5432
}
```

#### Tester connexion
```bash
psql -h db.xxx.supabase.co -U postgres -d postgres
# Entrer mot de passe quand demandé

# Si ça marche pas : problème réseau ou credentials
```

#### Vérifier firewall Supabase
1. Aller sur Supabase Dashboard → Settings → Database
2. Vérifier que ton IP est dans "Allowed IP addresses" (ou configurer `0.0.0.0/0` pour dev)

---

### Erreur : `duplicate key value violates unique constraint`

**Cause** : Tentative d'insert d'un tmdb_id qui existe déjà (rare, devrait être géré par upsert).

**Solution** :
```python
# Vérifier que le code utilise bien ON CONFLICT
# Dans clients/db.py :

def upsert_movie(...):
    query = """
        INSERT INTO movies (tmdb_id, ...)
        VALUES (...)
        ON CONFLICT (tmdb_id) DO UPDATE SET ...  # ← DOIT être présent
    """
```

**Si erreur persiste** :
```sql
-- Supprimer manuellement le doublon
DELETE FROM movies WHERE tmdb_id = 12345;

-- Relancer le pipeline
```

---

## 🤖 Erreurs Sentence Transformers

### Erreur : `Model download failed`

**Cause** : Connexion internet instable ou problème HuggingFace.

**Solution** :

#### Téléchargement manuel
```python
from sentence_transformers import SentenceTransformer

# Forcer téléchargement
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', 
                           cache_folder='./model_cache')
print("Model downloaded!")
```

#### Vérifier cache
```bash
# Le modèle devrait être ici après téléchargement
ls ~/.cache/torch/hub/sentence_transformers/

# Si dossier vide, réessayer download ou libérer espace disque
```

#### Utiliser proxy (si derrière firewall d'entreprise)
```bash
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

python pipelines/03_build_embeddings.py
```

---

### Erreur : `CUDA out of memory` (Si GPU disponible)

**Cause** : Batch size trop élevé pour ta GPU.

**Solution** :
```python
# Éditer pipelines/03_build_embeddings.py
embeddings = model.encode(texts, 
                         batch_size=16,  # Réduire (défaut: 32)
                         show_progress_bar=True)
```

**Forcer CPU** (plus lent mais stable) :
```python
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Désactiver GPU

model = SentenceTransformer('...')
model.to('cpu')
```

---

### Erreur : `File 'embeddings.npy' not found`

**Cause** : Pipeline 03 n'a jamais été exécuté ou crash avant sauvegarde.

**Solution** :
```bash
# Vérifier si fichier existe
ls data/embeddings/

# Si dossier vide, exécuter Pipeline 03
python pipelines/03_build_embeddings.py

# Le fichier devrait apparaître
ls -lh data/embeddings/movie_embeddings.npy
```

---

## 📂 Erreurs Fichiers & Paths

### Erreur : `FileNotFoundError: letterboxd-data.csv`

**Cause** : Fichier CSV mal placé ou mal nommé.

**Solution** :
```bash
# Vérifier structure
cd apps/ml
ls data/

# Doit contenir : letterboxd-data.csv (nom exact !)

# Si absent, copier ton export Letterboxd
cp ~/Downloads/letterboxd-xyz.csv data/letterboxd-data.csv
```

---

### Erreur : `PermissionError: [Errno 13] Permission denied`

**Cause** : Manque de droits d'écriture sur le dossier.

**Solution** :
```bash
# Vérifier permissions
ls -la data/embeddings/

# Donner droits d'écriture
chmod -R 755 data/

# Réessayer
python pipelines/03_build_embeddings.py
```

---

## 🧩 Erreurs Logiques / Données

### Problème : "No highly rated movies found"

**Cause** : Aucun film noté 8+ dans ta base.

**Solutions** :

#### Option 1 : Baisser le seuil
```python
# Éditer apps/ml/config/settings.py
MIN_RATING_FOR_SIMILAR = 7  # Au lieu de 8
```

#### Option 2 : Vérifier import Letterboxd
```sql
-- Compter films notés 8+
SELECT COUNT(*) FROM interactions WHERE rating >= 8;

-- Si 0, problème lors de l'import
-- Relancer Pipeline 01
```

---

### Problème : "Only 10 candidates generated (expected 2000)"

**Cause** : Pool de candidats trop petit.

**Solutions** :

#### Baisser MIN_RATING_FOR_SIMILAR
```python
MIN_RATING_FOR_SIMILAR = 6  # Plus inclusif
```

#### Augmenter SIMILAR_MOVIES_PER_FILM
```python
SIMILAR_MOVIES_PER_FILM = 50  # Au lieu de 20
```

#### Vérifier expansion TMDb
```python
# Vérifier logs de Pipeline 04
# Devrait afficher : "Expanding from X films → Y candidates"
# Si Y < 500, problème avec TMDb Similar endpoint
```

---

### Problème : Scores tous très bas (~0.3)

**Cause** : Profil utilisateur mal calculé ou embeddings corrompus.

**Diagnostic** :
```python
# Vérifier profil utilisateur (doit être non-null)
user_profile = calculate_user_profile(...)
print(np.linalg.norm(user_profile))  # Doit être > 0

# Vérifier embeddings
embeddings = np.load('data/embeddings/movie_embeddings.npy')
print(embeddings.shape)  # (N, 384)
print(np.isnan(embeddings).sum())  # Doit être 0
```

**Solution** : Régénérer embeddings
```bash
rm -rf data/embeddings/
python pipelines/03_build_embeddings.py
python pipelines/04_build_taste_candidates_full.py
```

---

## 🖥️ Erreurs Environnement

### Erreur : `ModuleNotFoundError: sentence_transformers`

**Cause** : Dépendances Python manquantes.

**Solution** :
```bash
cd apps/ml

# Vérifier environnement virtuel actif
which python
# Doit afficher : /path/to/apps/ml/.venv/bin/python

# Si pas actif
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Installer dépendances
pip install -r requirements.txt
```

---

### Erreur : `Python version mismatch`

**Cause** : Python < 3.10.

**Solution** :
```bash
# Vérifier version
python --version
# Doit être >= 3.10

# Si trop vieux, installer Python 3.11
# macOS : brew install python@3.11
# Recréer venv
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 📊 Logs & Debugging

### Activer Logs Verbeux

```python
# En haut de n'importe quel pipeline
import logging
logging.basicConfig(level=logging.DEBUG)

# Logs TMDb
import requests
requests.packages.urllib3.disable_warnings()  # Si SSL warnings gênants
```

### Exécuter en Mode Debug

```bash
# Avec pdb (debugger Python)
python -m pdb pipelines/01_import_letterboxd.py

# Breakpoint manuel dans le code
import pdb; pdb.set_trace()
```

### Vérifier État de la DB

```sql
-- Connexion
psql -h db.xxx.supabase.co -U postgres -d postgres

-- Statistiques
SELECT 
    'movies' as table, COUNT(*) FROM movies
UNION ALL SELECT 
    'movie_features', COUNT(*) FROM movie_features
UNION ALL SELECT 
    'interactions', COUNT(*) FROM interactions
UNION ALL SELECT 
    'taste_candidates', COUNT(*) FROM taste_candidates;
```

---

## 🆘 Ressources d'Aide

### Documentation Externe
- **TMDb API** : [https://developers.themoviedb.org/3](https://developers.themoviedb.org/3)
- **Sentence Transformers** : [https://www.sbert.net/docs/](https://www.sbert.net/docs/)
- **PostgreSQL** : [https://www.postgresql.org/docs/](https://www.postgresql.org/docs/)

### Forums Communautaires
- **TMDb Forum** : [https://www.themoviedb.org/talk](https://www.themoviedb.org/talk)
- **HuggingFace** : [https://discuss.huggingface.co](https://discuss.huggingface.co)
- **Supabase Discord** : [https://discord.supabase.com](https://discord.supabase.com)

---

## ✅ Checklist de Diagnostic

Si rien ne marche, suivre dans l'ordre :

- [ ] Python >= 3.10 installé
- [ ] Environnement virtuel activé
- [ ] `pip install -r requirements.txt` exécuté
- [ ] `.env.local` correctement configuré
- [ ] Clé TMDb valide (test avec curl)
- [ ] Tables PostgreSQL créées
- [ ] Connexion Supabase fonctionnelle (test avec psql)
- [ ] `letterboxd-data.csv` dans `data/`
- [ ] Dossier `data/embeddings/` avec droits d'écriture
- [ ] Modèle sentence-transformers téléchargé

Si tout ✅, les pipelines devraient marcher !

---

**Pas de solution trouvée ?** Vérifie les logs détaillés :
```bash
python pipelines/XX_pipeline.py 2>&1 | tee debug.log
# Partager debug.log si besoin d'aide
```
