# Pipeline 05: Build Emotion Vectors

**Script** : `apps/ml/pipelines/05_build_emotion_vectors.py`  
**Responsabilité** : Transformer les embeddings sémantiques des films en vecteurs d'émotions Plutchik (8 dimensions).

## 1. Objectif

Ce pipeline permet de quantifier la présence des 8 émotions primaires de Plutchik dans chaque film de la base de données. Il n'utilise pas de classification supervisée, mais une approche **Zero-shot** basée sur la similarité sémantique.

## 2. Fonctionnement Algorithmique

### A. Définition des Ancres (Anchors)
Pour chaque émotion primaire $E_i$, nous définissons un texte "ancre" $A_i$ riche sémantiquement, sans utiliser de mots-clés de genres ou de tropes, mais plutôt du vocabulaire sensoriel et émotionnel.

*Exemple pour "Peur"* :
> "Dread, anxiety, feeling unsafe. Sustained tension, looming threat, tight atmosphere. Makes you uneasy and on edge."

Ces définitions se trouvent dans `apps/ml/config/emotions.py`.

### B. Encodage
1. Les 8 ancres sont encodées en embeddings ($V_{anchor}$) via le modèle `sentence-transformers` (le même que pour les films).
2. Chaque film possède déjà son embedding sémantique ($V_{film}$) calculé précédemment.

### C. Calcul du Vecteur Émotionnel
Pour un film donné, on calcule la similarité cosinus avec chaque ancre :
$$ sim_i = \text{cosine}(V_{film}, V_{anchor_i}) $$

On applique ensuite un **Softmax avec Température** pour obtenir une distribution de probabilité :
$$ P(E_i) = \frac{\exp(sim_i / \tau)}{\sum_j \exp(sim_j / \tau)} $$

*   **Température ($\tau$)** : Réglée à `0.07` (très basse) pour augmenter le contraste et éviter d'avoir des distributions uniformes (tous à 0.125). Cela force le modèle à "choisir" les émotions dominantes.

### D. Métriques Dérivées
- **Confidence** : $P(top_1) - P(top_2)$. Mesure à quel point le film est "typé". Un film avec 0.8 en Joie et 0.1 en Tristesse a une haute confiance (0.7).
- **Entropie** : Mesure le désordre de la distribution.

## 3. Sortie (Output)

Le pipeline génère deux fichiers dans `data/emotions/` :

### `movie_emotions.parquet`
Fichier principal pour usage interne (Pandas), contenant :
- `tmdb_id`
- `e_joy`, `e_trust`, ... (Scores primaires)
- `d_ecstasy`, `d_terror`, ... (Scores des dyades d'intensité - *Note: Le frontend recalcule ses propres dyades*)
- `confidence`, `entropy`

*Ce fichier est ensuite converti en JSON optimisé pour l'application web.*

## 4. Configuration

Les paramètres sont centralisés dans `apps/ml/config/emotions.py` :
- `PRIMARY_EMOTIONS` : Textes des ancres.
- `EMOTION_TEMPERATURE` : Paramètre de contraste (0.07).
