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
