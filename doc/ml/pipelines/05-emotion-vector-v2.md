# Pipeline Vecteur Émotionnel v2 (Supervisé)

Ce pipeline remplace la détection d'émotions "basée sur les ancres" (non supervisée) par une approche de Machine Learning supervisée, entraînée sur des données labellisées par l'utilisateur.

## Objectif
Prédire la distribution de probabilité des 8 émotions primaires de Plutchik pour chaque film du catalogue.

## Architecture

Le pipeline se compose de trois étapes principales :

### 1. Construction du Dataset d'Entraînement (`05a_build_emotion_training_dataset.py`)
- **Entrée** : 
    - `movie_emotion_labels` (Vérité Terrain) : Labels soumis par l'utilisateur via l'interface d'entraînement.
    - `movie_embeddings.npy` : Embeddings textuels des métadonnées du film.
    - `anchor_embeddings.npy` : Embeddings des mots prototypiques des émotions.
- **Processus** :
    - **Anchor Logits** : Calcule la similarité cosinus entre l'embedding du film et les 8 ancres émotionnelles.
    - **Normalisation Z-Score** : Normalise ces logits en utilisant les statistiques de tout le catalogue pour gérer les différences de plages de valeurs.
    - **Ingénierie des Fonctionnalités** : Combine les logits normalisés avec les genres et mots-clés encodés (multi-hot encoding).
- **Sortie** : 
    - `train_X.parquet`, `train_y.parquet` : Données d'entraînement.
    - `feature_schema.json` : Métadonnées pour la reconstruction des fonctionnalités.

### 2. Entraînement du Modèle (`05b_train_emotion_model.py`)
- **Algorithme** : Régression Logistique (Multinomiale).
- **Configuration** :
    - `class_weight='balanced'` : Pour gérer le déséquilibre des classes (ex: moins de films "Peur").
    - `C=1.0` : Régularisation standard.
- **Métriques** : Suit l'Exactitude (Accuracy), l'Exactitude Top-2 et le score Macro-F1.
- **Sortie** : 
    - `emotion_v2.pkl` : Modèle Scikit-Learn sérialisé.
    - `model_metrics.json` : Rapport de performance.

### 3. Scoring du Catalogue (`05c_score_emotions_catalog.py`)
- **Processus** : 
    - Charge le modèle entraîné et le schéma des fonctionnalités.
    - Recalcule les fonctionnalités pour *chaque* film du catalogue (IDs TMDb).
    - Prédit la distribution de probabilité (8 flottants dont la somme vaut 1.0).
- **Dérivations** :
    - **Émotion Dominante** : L'émotion avec la probabilité la plus élevée.
    - **Confiance** : Différence entre la probabilité du 1er et du 2ème choix.
    - **Dyades** : Vérifie si les 2 premières émotions forment une dyade de Plutchik connue (ex: Joie + Confiance = Amour).
- **Sortie** : 
    - `movie_emotions.parquet` : Dataset complet pour analyse.
    - `movie_emotions.json` : JSON minifié pour l'application web.

## Pourquoi un JSON Statique ? (`movie_emotions.json`)

Nous générons un fichier JSON statique (`public/data/movie_emotions.json`) au lieu d'interroger la base de données pour les scores d'émotion à l'exécution.

### Raisonnement
1.  **Performance** : Lire un fichier JSON en mémoire (heap Node.js/Next.js) est des ordres de grandeur plus rapide qu'une jointure DB pour chaque requête de recommandation.
2.  **Stateless** : L'algorithme de recommandation est fortement calculé en mémoire. Avoir toutes les données d'émotion disponibles de manière synchrone simplifie la logique de scoring (`candidates.map(...)`).
3.  **Volume** : Même avec 10 000 films, la charge utile JSON reste gérable (~2-3MB gzippé), ce qui est acceptable pour un chargement côté serveur.
4.  **Découplage** : Le pipeline ML s'exécute de manière asynchrone. L'application web consomme simplement le dernier artefact sans dépendre de l'infrastructure ML.

### Schéma (`movie_emotions.json`)
Mappe l'ID TMDB vers un objet compact :
```json
{
  "12345": {
    "e": [0.1, 0.0, 0.5, ...], // Tableau de 8 probabilités (Joie, Confiance, Peur, Surprise, Tristesse, Dégoût, Colère, Anticipation)
    "c": 0.25 // Score de confiance
  }
}
```
L'émotion dominante et les dyades sont calculées à la volée par le frontend `mood-scorer.ts` en utilisant ce vecteur de probabilité.
