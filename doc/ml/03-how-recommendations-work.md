# 🎓 Comprendre le Moteur de Recommandation Apollo (V1.5)

> **Document pédagogique** — Explique comment Apollo recommande des films, de la donnée brute à la suggestion finale.

---

## 📖 Table des Matières

1. [Le Problème](#le-problème)
2. [La Solution : Embeddings + ML](#la-solution)
3. [Le Pipeline en Détail](#le-pipeline-en-détail)
4. [V1.5 : Ce qui change](#v15--ce-qui-change)
5. [FAQ Technique](#faq-technique)

---

## Le Problème

Tu as noté des centaines de films sur Letterboxd. Comment trouver automatiquement ceux que tu vas **adorer** parmi les milliers qui existent ?

### Les approches classiques (et leurs limites)

| Approche | Problème |
|----------|----------|
| **"Les gens qui ont aimé X ont aussi aimé Y"** | Cold start, effet bulle |
| **Filtrage par genre** | Trop grossier ("Thriller" ≠ "Thriller") |
| **Notes moyennes** | Populiste, ignore tes goûts |

---

## La Solution

Apollo combine **deux technologies** :

### 1. Embeddings (représentation sémantique)

Chaque film est transformé en un **vecteur de 384 nombres** qui capture son "essence" :

```
"The Matrix" → [0.12, -0.45, 0.78, ..., 0.33]  # 384 dimensions
```

Des films similaires ont des vecteurs proches (mesurable par **similarité cosinus**).

### 2. Machine Learning (apprentissage de préférences)

Un modèle XGBoost apprend **tes préférences personnelles** à partir de tes notes :
- Quels patterns de features → notes élevées ?
- Quels patterns → notes basses ?

---

## Le Pipeline en Détail

```mermaid
flowchart LR
    subgraph 1. Données
        A[Letterboxd CSV] --> B[Supabase DB]
        B --> C[TMDb API]
    end
    
    subgraph 2. Représentation
        C --> D[Synopsis + Métadonnées]
        D --> E[Embeddings 384D]
    end
    
    subgraph 3. Profil Utilisateur
        E --> F[Films aimés ≥9]
        F --> G[5 Centroids K-Means]
        E --> H[Films détestés ≤4]
        H --> I[Anti-Centroid]
    end
    
    subgraph 4. Features
        G --> J[cos_pos_c0...c4]
        J --> K[max/min/mean_cos_pos]
        I --> L[cos_to_neg_center]
        K --> M[pos_neg_margin]
    end
    
    subgraph 5. Scoring
        M --> N[XGBoost Classifier]
        N --> O[Expected Rating]
        O --> P[MMR Reranking]
        P --> Q[Top 200 Candidats]
    end
```

### Étape par étape

#### 1️⃣ Import des données (Pipeline 01)
- Lecture du CSV Letterboxd
- Matching avec l'ID TMDb de chaque film
- Stockage dans Supabase

#### 2️⃣ Enrichissement (Pipeline 02)
- Récupération via TMDb API :
  - Synopsis complet
  - Casting (acteurs, réalisateurs)
  - Genres et mots-clés

#### 3️⃣ Embeddings (Pipeline 03)
- Modèle : `paraphrase-multilingual-MiniLM-L12-v2`
- Input : texte combiné (synopsis + genres + cast)
- Output : vecteur 384 dimensions par film

#### 4️⃣ Construction du Profil (Pipeline 04b)

**Centroids Positifs** (K-Means sur films ≥9/10) :
```
Tes 48 films adorés → 4-5 "clusters" de goûts
Cluster 1 = Sci-fi cérébral (Matrix, Inception...)
Cluster 2 = Drame intimiste (Lost in Translation...)
Cluster 3 = Aventure épique (LOTR, Dune...)
...
```

**Anti-Centroid** (films ≤4/10) :
```
Tes 8 films détestés → 1 centroid "à éviter"
```

#### 5️⃣ Features Engineering

Pour chaque film candidat, on calcule :

| Feature | Signification |
|---------|---------------|
| `cos_pos_c0` | Distance au cluster 1 |
| `cos_pos_c1` | Distance au cluster 2 |
| `max_cos_pos` | Distance au cluster le plus proche |
| `mean_cos_pos` | Distance moyenne à tous les clusters |
| `cos_to_neg_center` | Distance à "ce que tu détestes" |
| `pos_neg_margin` | Écart entre positif et négatif |
| `genre_*` | Présence de chaque genre |
| `kw_*` | Présence de chaque mot-clé |
| `decade_*` | Décennie de sortie |

#### 6️⃣ Scoring (Pipeline 04c)

XGBoost prédit la **note attendue** (2-10) pour chaque candidat.

#### 7️⃣ Diversification (MMR)

Le top brut peut être trop homogène. MMR reranke pour la diversité :

```
MMR(film) = 0.7 × Score - 0.3 × Similarité_aux_déjà_sélectionnés
```

---

## V1.5 : Ce Qui Change

### Avant (V1)

- ✅ 5 centroids positifs
- ✅ `max_cos_pos` comme feature principale
- ❌ Aucune info sur les films détestés
- ❌ Pas de contrôle de diversité

### Après (V1.5)

- ✅ 5 centroids positifs + **1 anti-centroid**
- ✅ Features enrichies : `min_cos_pos`, `mean_cos_pos`, `cos_to_neg_center`, `pos_neg_margin`
- ✅ **MMR reranking** pour diversité

### Pourquoi c'est mieux ?

| Problème V1 | Solution V1.5 |
|-------------|---------------|
| "Ce film ressemble à ce que j'aime... mais aussi à ce que je déteste" | `pos_neg_margin` détecte ce cas |
| Top-10 = 10 films identiques | MMR garantit la variété |
| `max_cos_pos` trop dominant | `mean_cos_pos` complète le signal |

---

## FAQ Technique

### Combien de films faut-il avoir notés ?

| Films notés | Qualité |
|-------------|---------|
| < 20 | ⚠️ Insuffisant |
| 50-100 | ✅ Bon |
| 150+ | 🚀 Excellent |

### Pourquoi K-Means plutôt qu'une moyenne ?

Une moyenne "dilue" tes goûts variés. K-Means préserve **plusieurs profils** :
- Tu peux aimer Nolan ET Miyazaki → 2 clusters distincts

### Pourquoi MMR λ = 0.7 ?

| λ | Effet |
|---|-------|
| 1.0 | Score pur (risque d'homogénéité) |
| 0.7 | **Équilibré** (default) |
| 0.5 | Très divers (risque de recommandations hors-sujet) |

### Comment améliorer mes recommandations ?

1. **Noter plus de films** (surtout les extrêmes : 9-10 et 1-4)
2. **Relancer le pipeline** après chaque mise à jour
3. **Ajuster le seuil MMR** si le top-10 est trop uniforme

---

## 📚 Glossaire

| Terme | Définition |
|-------|------------|
| **Embedding** | Représentation vectorielle d'un texte/concept |
| **Centroid** | Centre d'un cluster (point moyen) |
| **Cosine Similarity** | Mesure de l'angle entre deux vecteurs (1 = identique, 0 = orthogonal) |
| **XGBoost** | Algorithme de gradient boosting (arbres de décision ensemblés) |
| **MMR** | Maximal Marginal Relevance — algorithme de diversification |
| **Anti-centroid** | Vecteur moyen des films détestés |

---

*Documentation mise à jour le 2026-02-04 — Apollo ML V1.5*
