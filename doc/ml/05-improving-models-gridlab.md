# Améliorer les Modèles avec GridLab : Intentions et Méthodologie

Ce guide explique la philosophie derrière l'outil "GridLab" et comment l'utiliser pour améliorer les performances de nos modèles de recommandation (`taste` et `emotion`) face à un problème spécifique : le bruit statistique sur de petites données.

## Le Problème : Le Mirage des "Gains"

Lorsqu'on travaille sur des datasets de taille réduite (ex: 156 films annotés), il est facile d'observer des améliorations artificielles. Ajouter une feature complexe, un hyper-paramètre ou une stratégie de pondération des classes peut faire gagner 2% de précision *par hasard* sur un jeu de test.

Cependant, ces gains s'évaporent souvent en production ou sur de nouvelles données. **L'instabilité est l'ennemi.**

### Pourquoi nous avons créé GridLab

L'objectif de GridLab est de dépasser l'approche "tâtonnement manuel" et de répondre par la méthode scientifique à des questions comme :

> *"Est-ce que les mots-clés (`keywords`) aident vraiment à prédire le goût, ou est-ce qu'ils ajoutent juste du bruit sur 150 exemples ?"*

> *"Est-ce que l'undersampling aide mes classes minoritaires, ou est-ce que je perds trop d'information ?"*

## La Méthodologie : Ablation & Stabilité

GridLab repose sur deux piliers :

1.  **L'Étude d'Ablation (Ablation Study) :**
    Au lieu de tout mélanger, nous testons des "blocs" de features incrémentaux.
    *   *Baseline :* Features minimales (ex: juste les Cosine Similarities).
    *   *Incremental :* On ajoute les Genres qui sont des features stables.
    *   *Complexe :* On ajoute les Mots-clés (KW) qui sont nombreux et bruyants.

    Si l'ajout d'un bloc n'améliore pas significativement la performance (ou augmente la variance), **on l'enlève**. Moins c'est mieux (Rasoir d'Ockham).

2.  **La Priorité à la Stabilité :**
    GridLab exécute une validation croisée stratifiée (Stratified K-Fold CV) 5 fois.
    Il ne regarde pas seulement la moyenne de la performance (ex: MAE), mais aussi l'**écart-type (std)**.
    
    *   Config A : MAE = 1.10 ± 0.05
    *   Config B : MAE = 1.08 ± 0.25 (Meilleure moyenne, mais instable ⚠️)
    
    GridLab pénalisera la Config B via son "coefficient de variation" (CV coeff).

## Comment Lire un Rapport GridLab

Chaque exécution génère un rapport Markdown. Voici les éléments clés à surveiller :

### 1. Le Vainqueur (Winner)

```
🏆 Recommended: taste__COS_POS+NEG__bal=none
   mae: 1.109 ± 0.187
   Features: 9
```
*   **Balancing = `none` ?** Surprenant pour des données déséquilibrées ? Pas forcément. Sur de petits échantillons, les techniques comme `SMOTE` ou `class_weight` peuvent sur-apprendre sur le bruit des classes minoritaires. Si `none` gagne, c'est que le modèle simple généralise mieux.
*   **Features : 9 ?** Seulement 9 features gagnent contre 300+ mots-clés ? C'est le signal que les mots-clés introduisent trop de variabilité pour la taille actuelle du dataset. C'est une information précieuse : **on ne doit pas les utiliser pour l'instant.**

### 2. Le Tableau de Classement

Regardez la colonne **MAE ↓** (pour `taste`) ou **Top-2 ↑** (pour `emotion`).
Si les écarts entre le 1er et le 5ème sont minimes (< 0.02), alors les choix sont statistiquement équivalents. Dans ce cas, choisissez toujours la config avec le moins de **Feats** (features).

### 3. Les Insights Automatiques

GridLab analyse les résultats pour vous donner des conseils en langage naturel :
*   `⚠️ KW features DEGRADE mae` : Confirme que le modèle est pollué par les mots-clés.
*   `✅ NEG block improves within±1` : Confirme une hypothèse métier (ex: "savoir ce que l'utilisateur déteste aide à prédire ce qu'il aime").

## Workflow de l'Ingénieur ML

Comment intégrer GridLab dans votre cycle de développement :

1.  **Hypothèse :** "Je pense que l'ajout des réalisateurs (Directors) améliorerait le modèle."
2.  **Implémentation :** Ajoutez la feature dans le pipeline (`04b` ou `05a`) pour qu'elle soit dans le Parquet.
3.  **Configuration :** Ajoutez un bloc `DIRECTOR` dans `gridlab.py` pointant vers la nouvelle colonne.
4.  **Test Rapide :** `python tools/gridlab.py --task taste --dry-run`
5.  **Expérience :** `python tools/gridlab.py --task taste`
6.  **Décision :**
    *   Si GridLab dit que `DIRECTOR` améliore le score ET la stabilité -> **Adopter**.
    *   Sinon -> **Rejeter** (ne pas polluer le modèle de prod).

C'est ainsi que nous garantissons une amélioration continue et maîtrisée de nos algorithmes de recommandation.

---

## Changements Appliqués (10/02/2026) — Suite aux Rapports GridLab

Les rapports générés (`gridlab_taste_20260210_132426.md` et `gridlab_emotion_20260210_132731.md`) ont révélé des optimisations significatives. Voici ce qui a été modifié :

### 🎯 Modèle Taste (XGBoost – Ordinal Classification)

| Avant | Après | Impact |
|-------|-------|--------|
| ~340 features (COS+META+GENRE+KW300) | **9 features** (COS_POS+NEG) | MAE 1.577 → **1.109** |
| `TOP_KEYWORDS = 300` | `TOP_KEYWORDS_TASTE = 0` | KW dégradaient le MAE |
| Tous les blocs activés | `TASTE_FEATURE_BLOCKS = ["COS_POS", "NEG"]` | -97% de features |
| Balancing variable | `TASTE_BALANCING = "none"` | Meilleure généralisation |

**Insight clé** : Les mots-clés et les métadonnées (année, langue, décennie, genres) introduisaient du bruit sur notre petit dataset (156 films). Le modèle le plus simple, basé uniquement sur les similarités cosinus (centroids positifs + anti-centroid), généralise nettement mieux.

### 😊 Modèle Emotion (Logistic Regression – Multi-class)

| Avant | Après | Impact |
|-------|-------|--------|
| `TOP_KEYWORDS = 300` | `TOP_KEYWORDS_EMOTION = 100` | CV coeff 0.080 → 0.053 |
| `class_weight="balanced"` | **Supprimé** (`bal=none`) | Top-2: 60.9% → **64.7%** |
| `EMOTION_FEATURE_BLOCKS` implicite | `["ANCHOR", "GENRE", "KW"]` explicite | 127 features |

**Insight clé** : Le `class_weight="balanced"` faisait sur-apprendre sur les classes minoritaires. Le modèle sans balancing est plus stable (+3.8% Top-2). Les KW(100) apportent un léger gain de F1 vs KW(0), mais KW(300) introduisait trop de variance.

### Fichiers Modifiés

| Fichier | Changement |
|---------|------------|
| `config/settings.py` | Nouveaux paramètres : `TOP_KEYWORDS_TASTE`, `TOP_KEYWORDS_EMOTION`, `TASTE_BALANCING`, `EMOTION_BALANCING`, `TASTE_FEATURE_BLOCKS`, `EMOTION_FEATURE_BLOCKS` |
| `pipelines/04b_build_training_dataset.py` | Feature building conditionnel basé sur `TASTE_FEATURE_BLOCKS` |
| `pipelines/04c_train_and_score_xgboost.py` | Scoring conditionnel, lit `feature_blocks` du schéma sauvegardé |
| `pipelines/05a_build_emotion_training_dataset.py` | `TOP_KEYWORDS_EMOTION = 100` au lieu de 300 |
| `pipelines/05b_train_emotion_model.py` | Suppression de `class_weight="balanced"` |

### ⚠️ Re-training Requis

Ces changements ne prennent effet qu'après un re-training complet :

```bash
# 1. Taste: rebuild dataset + retrain
python pipelines/04b_build_training_dataset.py
python pipelines/04c_train_and_score_xgboost.py

# 2. Emotion: rebuild dataset + retrain + rescore
python pipelines/05a_build_emotion_training_dataset.py
python pipelines/05b_train_emotion_model.py
python pipelines/05c_score_emotions_catalog.py
```
