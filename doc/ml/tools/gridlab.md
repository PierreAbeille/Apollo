# Grid Balancing Lab - Référence Technique

Ce document est le miroir technique de l'outil `tools/gridlab.py`, conçu pour exécuter des expériences d'ablation et de stratégies d'équilibrage de classes de manière reproductible.

## Objectif

GridLab est un "laboratoire" CLI (Command Line Interface) qui permet de :
1.  **Tester systématiquement** des combinaisons de features (Feature Groups).
2.  **Comparer des stratégies** de gestion du déséquilibre des classes (`none`, `class_weight`, `undersample`).
3.  **Générer des rapports** clairs (JSON & Markdown) avec sélection automatique du "meilleur" modèle selon plusieurs critères (performance, stabilité, simplicité).

## Usage

L'outil s'exécute depuis la racine du projet ML (`apps/ml`).

```bash
# Activation de l'environnement virtuel
source .venv/bin/activate

# Aperçu du plan d'expérience (sans exécution)
python tools/gridlab.py --task taste --dry-run

# Lancer l'expérience complète pour 'taste' (XGBoost)
python tools/gridlab.py --task taste --output reports/

# Lancer l'expérience complète pour 'emotion' (Logistic Regression)
python tools/gridlab.py --task emotion --output reports/
```

### Arguments CLI

| Argument | Défaut | Description |
|---|---|---|
| `--task` | *Requis* | `taste` ou `emotion`. Définit le pipeline et le modèle à utiliser. |
| `--kw-sizes` | `0,100,300` | Tailles du vocabulaire de mots-clés à tester. `0` désactive le bloc KW. |
| `--balancing` | `none,class_weight,undersample` | Stratégies d'équilibrage à tester. |
| `--cv` | `5` | Nombre de plis pour la validation croisée stratifiée (Stratified K-Fold). |
| `--seed` | `42` | Graine aléatoire pour la reproductibilité (split CV, undersampling). |
| `--output` | `reports/` | Dossier de sortie pour les fichiers `.json` et `.md`. |
| `--max-configs` | `20` | Sécurité pour éviter l'explosion combinatoire. Utilisez `--force` pour dépasser. |
| `--force` | `False` | Ignore la limite de `max-configs`. |
| `--dry-run` | `False` | Affiche uniquement la liste des configurations qui seraient testées. |

## Blocs de Features

Le cœur de GridLab repose sur la définition de "Blocs" de features, qui sont activés ou désactivés pour tester leur impact marginal.

### Task: `taste` (XGBoost Ordinal)

| Bloc | Description | Préfixes de Colonnes |
|---|---|---|
| **COS_POS** | Similitudes cosinus avec les centroïdes positifs + stats (max/min/mean). | `cos_pos_c*`, `max_…`, `min_…`, `mean_…` |
| **NEG** | Distance au centroïde négatif et marge de séparation. | `cos_to_neg_center`, `pos_neg_margin` |
| **META** | Métadonnées du film normalisées. | `lang_*`, `decade_*`, `release_year_normalized` |
| **GENRE** | Genres (One-Hot / Multi-Hot). | `genre_*` |
| **KW** | Mots-clés (Top N). | `kw_*` (filtré par `--kw-sizes`) |

### Task: `emotion` (Logistic Regression)

| Bloc | Description | Préfixes de Colonnes |
|---|---|---|
| **ANCHOR** | Logits (distances z-score) vers les 8 ancres émotionnelles. | `anchor_*` |
| **GENRE** | Genres (One-Hot / Multi-Hot). | `genre_*` |
| **KW** | Mots-clés (Top N). | `kw_*` (filtré par `--kw-sizes`) |
| *(META)* | *Non utilisé pour 'emotion' (pas de colonnes lang/decade).* | |

## Stratégies d'Équilibrage

| Stratégie | Implémentation |
|---|---|
| **none** | Pas d'intervention. Les poids des classes sont égaux. |
| **class_weight** | **Taste (XGB)**: Utilise `sample_weight` calculé inversement proportionnel à la fréquence.<br>**Emotion (LogReg)**: Utilise le paramètre `class_weight='balanced'` de Scikit-Learn. |
| **undersample** | Sous-échantillonnage aléatoire (RandomUndersampler) pour ramener la classe majoritaire au niveau médian. |

## Métriques et Sélection du Vainqueur

GridLab sélectionne automatiquement la meilleure configuration selon une hiérarchie de critères :

**Pour `taste` :**
1.  **MAE (Mean Absolute Error) ↓** : Minimiser l'erreur moyenne est la priorité.
2.  **Stabilité (Std MAE) ↓** : À performance égale, on préfère le modèle le plus constant entre les plis.
3.  **Complexité ↓** : À performance égale, on préfère moins de features (Rasoir d'Ockham).

**Pour `emotion` :**
1.  **Top-2 Accuracy ↑** : Maximiser la chance que la vraie émotion soit dans les 2 prédictions principales.
2.  **Macro F1 ↑** : Assurer une bonne performance sur toutes les classes, pas juste les majoritaires.
3.  **Stabilité (Std Top-2) ↓**.
4.  **Complexité ↓**.

## Sorties

Chaque exécution génère deux fichiers horodatés :
1.  `gridlab_<task>_<timestamp>.json` : Données brutes complètes, y compris les résultats par pli.
2.  `gridlab_<task>_<timestamp>.md` : Rapport lisible avec tableau de classement, analyse de stabilité et recommandation finale.
