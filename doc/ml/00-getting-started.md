# Guide ML pour Débutants Absolus

> **Objectif** : Comprendre le système de recommandation Apollo sans aucune connaissance préalable en Machine Learning, Deep Learning ou IA.

---

## 🤔 Pourquoi ce guide ?

Tu es un développeur qui connaît peut-être JavaScript, Python ou d'autres langages, mais le **Machine Learning** te semble mystérieux ? Pas de panique. Apollo utilise une approche ML **ultra-simplifiée** qui ne nécessite :
- ❌ Pas d'entraînement de modèle
- ❌ Pas de GPU
- ❌ Pas de mathématiques avancées
- ✅ Juste l'utilisation d'un **modèle pré-entraîné**

Pense à ça comme utiliser une bibliothèque (genre `lodash` ou `axios`) — quelqu'un d'autre a fait le travail difficile, tu l'utilises juste.

---

## 🎯 Le Problème qu'Apollo Résout

**Scénario classique** :
1. Tu as noté 200 films sur Letterboxd
2. Tu veux découvrir de nouveaux films qui te plairaient
3. Netflix te recommande toujours les mêmes blockbusters populaires
4. Les petits films incroyables restent invisibles

**Solution Apollo** :
1. Analyse tes films préférés (notes 8+)
2. Comprend **pourquoi** tu les aimes (thèmes, ambiance, style)
3. Trouve des films similaires **même s'ils sont peu connus**
4. Te les présente avec un score de pertinence

**Comment on fait ça ?** Avec des **embeddings sémantiques**.

---

## 🧩 Concepts de Base (Expliqués Simplement)

### 1. Texte → Nombres

Les ordinateurs ne comprennent pas le texte brut. Pour analyser "un film sombre sur le temps", il faut le convertir en nombres.

**Approche naïve** (ce qu'on NE fait PAS) :
```
"Donnie Darko" → Compter les mots : {donnie: 1, darko: 1}
```
❌ Problème : Ça ne capture pas le sens, juste la fréquence.

**Approche ML** (ce qu'on FAIT) :
```
"Donnie Darko is a dark psychological thriller about time travel and teenage angst"
↓
[0.234, -0.112, 0.456, 0.789, ..., -0.321] (384 nombres)
```
✅ Avantage : Ce **vecteur** (liste de nombres) capture le **sens sémantique**.

**💡 Analogie** : Imagine que chaque nombre représente un "axe" de signification :
- Position 0 : "Darkness level" (0.234 = assez sombre)
- Position 1 : "Time travel" (-0.112 = un peu de paradoxe temporel)
- Position 2 : "Teenager focus" (0.456 = oui, adolescent)
- ... 381 autres dimensions

---

### 2. Embeddings (Vecteurs Sémantiques)

**Définition simple** : Un embedding est une **représentation numérique** d'un texte qui capture son **sens**.

**Propriété magique** : Deux textes similaires auront des vecteurs proches.

**Exemple** :
```
"Dark psychological thriller" → [0.8, -0.3, 0.5, ...]
"Suspenseful mind-bending drama" → [0.75, -0.25, 0.48, ...]
"Romantic comedy" → [-0.2, 0.9, -0.6, ...]
```

Les deux premiers vecteurs sont **proches** (distance faible).  
Le troisième est **loin** (sens complètement différent).

**Comment Apollo les utilise** :
1. Chaque film devient un vecteur (via son synopsis)
2. On compare les vecteurs pour trouver les films similaires
3. Pas besoin de tags manuels type "Genre: Thriller"

---

### 3. Similarité Cosinus

**Problème** : Comment mesurer si deux vecteurs sont "similaires" ?

**Solution** : Similarité cosinus (mesure l'angle entre deux vecteurs).

**Formule (pas besoin de la retenir)** :
```
similarity = (A · B) / (||A|| × ||B||)
```

**Interprétation** :
- `1.0` : Identique
- `0.8` : Très similaire
- `0.5` : Moyennement similaire
- `0.0` : Aucun lien
- `-1.0` : Opposé

**💡 Analogie** : Imagine deux flèches dans l'espace :
- Flèches pointant dans la même direction = similarité élevée
- Flèches perpendiculaires = similarité faible

**Dans Apollo** :
```python
# Ton profil utilisateur (moyenne de tes films 8+)
user_profile = [0.7, -0.2, 0.5, ...]

# Un film candidat
candidate_film = [0.68, -0.18, 0.52, ...]

# Calcul
similarity = cosine_similarity(user_profile, candidate_film)
# Résultat : 0.89 → Film très compatible !
```

---

### 4. Modèles Pré-Entraînés

**Question** : Comment convertir texte → embedding ?

**Réponse courte** : On utilise un **modèle pré-entraîné** (comme une bibliothèque open-source).

**Nom du modèle Apollo** : `paraphrase-multilingual-MiniLM-L12-v2`

**Ce que ça fait** :
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
embedding = model.encode("A dark film about time travel")

# Résultat : array de 384 nombres
print(embedding.shape)  # (384,)
```

**Pourquoi "pré-entraîné" ?**
- Quelqu'un a déjà entraîné ce modèle sur des millions de phrases
- Il "comprend" le sens des mots et leur contexte
- **Tu n'as rien à entraîner** — télécharge et utilise

**💡 Analogie** : C'est comme utiliser Google Translate. Tu n'as pas créé l'IA de traduction, tu l'utilises juste.

---

## 🔄 Le Pipeline Apollo en 4 Étapes

### Vue d'Ensemble

```
[Letterboxd CSV] 
    ↓ 01_import
[Base de Données PostgreSQL]
    ↓ 02_sync_features
[Métadonnées TMDb (synopsis, cast, genres)]
    ↓ 03_build_embeddings
[Vecteurs 384D pour chaque film]
    ↓ 04_build_candidates
[Top 2000 recommandations personnalisées]
```

Chaque "flèche" est un **script Python** que tu peux exécuter.

---

### Étape 01 : Import Letterboxd

**Fichier** : `pipelines/01_import_letterboxd.py`

**Input** : `data/letterboxd-data.csv` (ton export)

**Output** : Table `movies` remplie + Table `interactions` remplie

**Ce qu'il fait** :
1. Lit le CSV ligne par ligne
2. Pour chaque film, recherche son **TMDb ID** via l'API TMDb (par titre + année)
3. Insert dans `movies` (tmdb_id, titre, année, poster)
4. Insert dans `interactions` (ta note, si tu l'as vu, etc.)

**💡 Analogie** : Comme importer des contacts dans ton téléphone depuis un fichier CSV.

**Exemple de sortie** :
```
Processing 200 letterboxd entries...
✓ Found: The Matrix (1999) → tmdb_id: 603
✓ Found: Donnie Darko (2001) → tmdb_id: 141
...
✓ Imported 198/200 films (2 skipped - no TMDb match)
```

---

### Étape 02 : Enrichissement TMDb

**Fichier** : `pipelines/02_sync_tmdb_features.py`

**Input** : Table `movies` (juste tmdb_id)

**Output** : Table `movie_features` remplie (synopsis, genres, cast, keywords)

**Ce qu'il fait** :
1. Parcourt tous les films dans `movies`
2. Pour chaque film, appelle TMDb API :
   ```
   GET /movie/{id}?language=en-US&append_to_response=credits,keywords
   ```
3. Extrait :
   - `overview` (synopsis)
   - `genres` (Science-Fiction, Drame, etc.)
   - `keywords` (time travel, dystopia, etc.)
   - `cast` (10 premiers acteurs)
   - `crew` (réalisateur)
4. Construit un `text_for_embedding` :
   ```
   Genres: Science Fiction, Drama. 
   Keywords: time travel, psychological thriller. 
   Cast: Jake Gyllenhaal, Jena Malone. 
   Director: Richard Kelly. 
   Overview: Donnie Darko is a troubled teenager...
   ```
5. Sauvegarde tout dans `movie_features`

**Pourquoi en anglais ?**
Les modèles d'embeddings sont meilleurs en anglais (plus de données d'entraînement).

**💡 Analogie** : Comme récupérer les métadonnées d'une chanson via Spotify API (durée, genre, artistes similaires).

---

### Étape 03 : Génération des Embeddings

**Fichier** : `pipelines/03_build_embeddings.py`

**Input** : Table `movie_features.text_for_embedding`

**Output** : Fichiers locaux (`data/embeddings/movie_embeddings.npy`)

**Ce qu'il fait** :
1. Charge le modèle sentence-transformers
2. Pour chaque film, encode le `text_for_embedding` :
   ```python
   text = "Genres: Sci-Fi. Keywords: time travel..."
   embedding = model.encode(text)  # Array de 384 nombres
   ```
3. Sauvegarde tous les embeddings dans un fichier `.npy` (format NumPy)
4. Crée un mapping `tmdb_id → index` pour retrouver les vecteurs

**Pourquoi sauvegarder ?**
Générer des embeddings prend du temps (quelques secondes pour 1000 films). En les sauvegardant, on ne recalcule jamais deux fois.

**💡 Analogie** : Comme créer un index de recherche (genre Algolia ou Elasticsearch) pour accélérer les futures requêtes.

**Exemple de sortie** :
```
Loading model paraphrase-multilingual-MiniLM-L12-v2...
Encoding 450 movies...
[████████████████████] 100% (450/450) - 00:45
✓ Saved embeddings: data/embeddings/movie_embeddings.npy
✓ Saved index: data/embeddings/tmdb_to_index.json
```

---

### Étape 04 : Calcul des Recommandations

**Fichier** : `pipelines/04_build_taste_candidates_full.py`

**Input** :
- Table `interactions` (tes notes)
- Fichier `movie_embeddings.npy`

**Output** : Table `taste_candidates` (2000 meilleurs films recommandés)

**Ce qu'il fait** :

#### 1. Calcul du Profil Utilisateur
```python
# Récupérer tes films notés 8+
highly_rated = get_films_with_rating_above(8)

# Récupérer leurs embeddings
embeddings_list = [get_embedding(film.tmdb_id) for film in highly_rated]

# Calculer la moyenne (= ton "profil idéal")
user_profile = np.mean(embeddings_list, axis=0)
# Résultat : [0.65, -0.22, 0.48, ...] (384D)
```

**💡 Analogie** : Si tu aimes 10 chansons, ton "profil musical" est la moyenne de leurs caractéristiques (tempo, tonalité, etc.).

#### 2. Expansion des Candidats
```python
# Pour chaque film noté 8+, demander à TMDb des films similaires
for film in highly_rated:
    similar = tmdb_api.get_similar_movies(film.tmdb_id)
    candidates.extend(similar)  # Ajouter à la liste
```

**Résultat** : ~5000 films candidats (beaucoup de doublons)

#### 3. Scoring
```python
for candidate_film in unique_candidates:
    # Récupérer son embedding
    candidate_emb = get_embedding(candidate_film.tmdb_id)
    
    # Calculer similarité avec ton profil
    score = cosine_similarity(user_profile, candidate_emb)
    
    # Sauvegarder (tmdb_id, score)
    results.append((candidate_film.tmdb_id, score))
```

#### 4. Top 2000
```python
# Trier par score décroissant
results.sort(key=lambda x: x[1], reverse=True)

# Garder les 2000 meilleurs
top_2000 = results[:2000]

# Sauvegarder dans taste_candidates
save_to_db(top_2000)
```

**💡 Analogie** : Comme Google qui classe les pages web par pertinence par rapport à ta requête.

---

## 🎬 Exemple Concret de Bout en Bout

### Contexte
Tu as noté "Inception" (10/10) sur Letterboxd.

### Pipeline

**01 - Import** :
```
Letterboxd CSV → "Inception, 2010, 10/10"
TMDb Search → tmdb_id: 27205
DB Insert → movies: {27205, "Inception", 2010, "/poster.jpg"}
DB Insert → interactions: {27205, rating: 10}
```

**02 - Features** :
```
TMDb API → GET /movie/27205?append_to_response=credits,keywords
Extraction → 
  Overview: "A thief who steals corporate secrets..."
  Genres: [{id: 28, name: "Action"}, {id: 878, name: "Science Fiction"}]
  Keywords: [{id: 1234, name: "dream"}, {id: 5678, name: "heist"}]
  Cast: ["Leonardo DiCaprio", "Marion Cotillard", ...]
  Director: "Christopher Nolan"
  
Text construction → "Genres: Action, Science Fiction. Keywords: dream, heist. 
                      Cast: Leonardo DiCaprio, Marion Cotillard. 
                      Director: Christopher Nolan. 
                      Overview: A thief who steals corporate secrets..."
                      
DB Insert → movie_features: {27205, lang: "en", text_for_embedding: "..."}
```

**03 - Embeddings** :
```
model.encode(text_for_embedding)
↓
[0.234, -0.567, 0.891, ..., -0.123] (384 nombres)
↓
Fichier: embeddings[index_421] = [0.234, ...]
Mapping: tmdb_to_index[27205] = 421
```

**04 - Recommendations** :
```
1. Profil utilisateur:
   Films 10/10 : [Inception]
   user_profile = embedding[421] = [0.234, -0.567, ...]

2. Candidats:
   TMDb Similar to Inception → [Interstellar, The Prestige, Shutter Island, ...]
   Fetch leurs embeddings

3. Scoring:
   Interstellar: cosine(user_profile, emb_interstellar) = 0.92
   The Prestige: cosine(user_profile, emb_prestige) = 0.88
   Shutter Island: cosine(user_profile, emb_shutter) = 0.85
   ...

4. Top 2000:
   1. Interstellar (0.92)
   2. The Prestige (0.88)
   3. Shutter Island (0.85)
   ...

DB Insert → taste_candidates: [{tmdb: 157336, score: 0.92}, ...]
```

**Résultat dans l'app web** :
```
[Tableau /recommandations]
#1 Interstellar (2014) - Match: 92% 🎯
#2 The Prestige (2006) - Match: 88%
#3 Shutter Island (2010) - Match: 85%
```

---

## 🚀 Comment Lancer le Pipeline ?

### Setup Initial (Une Fois)

```bash
cd apps/ml

# Environnement virtuel
python -m venv .venv
source .venv/bin/activate

# Dépendances
pip install -r requirements.txt

# Configuration
cp .env.example .env.local
# Éditer .env.local avec ta clé TMDb

# Éditer utils/database.py avec tes credentials Supabase
```

### Exécution du Pipeline Complet

```bash
# 1. Place ton fichier letterboxd-data.csv dans data/
# 2. Lance les scripts dans l'ordre

python pipelines/01_import_letterboxd.py
# Attendre ~2 min (dépend du nombre de films)

python pipelines/02_sync_tmdb_features.py
# Attendre ~5-10 min (API calls)

python pipelines/03_build_embeddings.py
# Attendre ~1-2 min (encoding)

python pipelines/04_build_taste_candidates_full.py
# Attendre ~10-15 min (expansion + scoring)
```

### Renouvellement Rapide

Si tu as ajouté de nouvelles notes sur Letterboxd :

```bash
python pipelines/01_import_letterboxd.py  # Import nouveaux films
python pipelines/04_build_taste_candidates_full.py  # Recalcul
# Pas besoin de refaire 02 et 03 (déjà en cache)
```

---

## 🐛 Que Faire si Ça Ne Marche Pas ?

### Erreur : "TMDB API Rate Limit"
**Cause** : Trop de requêtes trop vite  
**Solution** : Augmenter `TMDB_RATE_LIMIT_DELAY` dans `config/settings.py`

### Erreur : "Model download failed"
**Cause** : Connexion internet instable  
**Solution** : Réessayer, le modèle va dans `~/.cache/torch/`

### Erreur : "Database connection refused"
**Cause** : Mauvais credentials Supabase  
**Solution** : Vérifier `utils/database.py`, tester avec `psql`

### Erreur : "No embeddings found"
**Cause** : Pipeline 03 pas exécuté  
**Solution** : Lancer `python pipelines/03_build_embeddings.py`

Voir [`doc/ml/troubleshooting.md`](troubleshooting.md) pour plus de détails.

---

## 📚 Prochaines Étapes

Maintenant que tu comprends les bases :

1. **[Concepts ML Détaillés](01-what-is-ml.md)** : Plonge plus profondément dans les embeddings
2. **[Vue d'Ensemble des Pipelines](02-pipeline-overview.md)** : Diagramme visuel du flux
3. **[Documentation des Pipelines](pipelines/)** : Détails de chaque script

---

## 💡 Résumé en 3 Phrases

1. On convertit les synopsis de films en **vecteurs numériques** (embeddings) qui capturent leur sens
2. On calcule ton **profil utilisateur** (moyenne des vecteurs de tes films préférés)
3. On trouve les films dont les vecteurs sont **proches** de ton profil (similarité cosinus élevée)

**C'est tout le Machine Learning d'Apollo !** 🎉
