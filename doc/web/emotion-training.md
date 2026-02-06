# Emotion Training System

**Route UI** : `/emotion-training`  
**Table DB** : `movie_emotion_labels`

Ce module permet aux utilisateurs de labelliser rapidement les émotions ressenties ou transmises par les films qu'ils ont vus, afin de constituer un dataset "Vérité Terrain" pour l'entraînement ou l'affinement des modèles ML.

## 1. Architecture

### Backend (Next.js API + Supabase)

- **Service** : `services/emotion-training-service.ts`
    - gère la logique de récupération des films (filtre `is_done=true`).
    - gère la sauvegarde et l'annulation (undo).
    - utilise un "Seed" pour garantir un ordre aléatoire mais stable durant une session.

- **API Routes** :
    - `GET /api/emotion-training/movies` : Liste paginée/shuflée des films.
    - `POST /api/emotion-training/label` : Insert/Upsert un label.
    - `POST /api/emotion-training/undo` : Supprime le dernier label créé.
    - `GET /api/emotion-training/progress` : Statistiques simples.

### Frontend (Client Components)

L'interface est conçue pour la **vitesse** (High Velocity Labeling).

- **Grid** : 8 boutons correspondant aux émotions primaires de Plutchik.
- **Navigation Clavier** :
    - `1-8` : Sélection directe de l'émotion.
    - `→` : Passer (Skip).
    - `←` : Revenir (localement).
    - `Cmd+Z` : Annuler le dernier label (appel API undo).
- **Feedback** : Toast de confirmation non-intrusif.

## 2. Modèle de Données

```sql
ENUM primary_emotion: 'joy', 'trust', 'fear', 'surprise', 'sadness', 'disgust', 'anger', 'anticipation'
ENUM label_kind: 'transmitted' (défaut), 'felt'

Table movie_emotion_labels:
- tmdb_id (FK)
- emotion (primary_emotion)
- label_kind
- confidence_self (1-3)
- source ('emotion-training-ui')
```

## 3. Guide d'utilisation

1. Se rendre sur `/emotion-training`.
2. Le système charge les films vus non labellisés.
3. Pour chaque film, cliquer sur l'émotion dominante ou utiliser les touches `1` à `8`.
4. Le passage au film suivant est automatique.
