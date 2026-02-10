# Filtrage par Humeur (Mood Filtering)

Ce document détaille le fonctionnement technique du système de filtrage par humeur implémenté dans l'application web Apollo.

## Vue d'ensemble

Le système permet de filtrer les recommandations de films selon l'état émotionnel de l'utilisateur. Contrairement à une simple recherche par genre, ce système utilise une approche psychologique basée sur la roue des émotions de Plutchik et un filtrage statistique par percentiles.

## Architecture "Taste First"

Un principe fondamental de notre architecture est que **le goût prévaut sur l'humeur**. 

1. **Pré-sélection (Taste)** : Nous récupérons d'abord les ~300 meilleurs films pour l'utilisateur, basés uniquement sur son profil de goûts (Taste Score).
2. **Filtrage (Mood)** : Nous appliquons ensuite un filtre d'humeur sur cet ensemble restreint.

Cela garantit que l'utilisateur ne se voit jamais recommander un film qui correspond à son humeur mais qu'il détesterait (mauvais film, genre détesté, etc.).

## Modèle de Plutchik

Nous utilisons le modèle des émotions de Robert Plutchik qui définit :
- **8 Émotions Primaires** : Joie, Confiance, Peur, Surprise, Tristesse, Dégoût, Colère, Anticipation.
- **Dyades** : Combinaisons de deux émotions primaires adjacentes (ex: Joie + Confiance = Amour).

### Structure des Données

Les données d'émotions sont stockées dans `public/data/movie_emotions.json` généré par le pipeline ML.

```typescript
interface FilmEmotions {
    e: number[]; // Vecteur de 8 scores [0-1] correspondant aux 8 émotions primaires
    c: number;   // Score de confiance
}
```

## Algorithme de Scoring V2 (Vecteur Cible)

Depuis la v2 (Février 2026), nous n'utilisons plus de percentiles statiques stockés en base, mais un **calcul de similarité dynamique** côté client/serveur.

### 1. Construction du Vecteur Cible ($V_{target}$)
Selon la position du slider (facteur $f \in [0, 1]$) :
$$ V_{target} = f \cdot V_{regulation} + (1-f) \cdot V_{congruence} $$

### 2. Scoring des Candidats
Pour chaque film candidat $M$ ayant un vecteur émotion $V_{movie}$ :
$$ Score(M) = CosineSimilarity(V_{target}, V_{movie}) $$

### 3. Tri et Filtrage
- Les films sont triés par ce score décroissant.
- Le toggle "Intensité" filtre simplement les résultats pour ne garder que ceux ayant une similarité suffisante (ou affiner la sélection).

## Interface Utilisateur

### Sélecteur d'Émotions (`GenreMoodFilter`)
- Permet de choisir 1 ou 2 émotions primaires.
- Si 2 émotions adjacentes sont choisies, l'interface indique la Dyade correspondante (ex: "Amour").
- **Régulation Continue (Slider 0-100)** :
  - Remplace les presets discrets par un contrôle fin.
  - **0 (Congruence)** : Cible = Vecteur de l'émotion choisie.
  - **100 (Régulation/Antidote)** : Cible = Vecteur opposé (mélange pondéré défini dans `mood-scorer.ts`).
  - **Interpolation** : Le vecteur cible est une interpolation linéaire entre le vecteur Congruence et le vecteur Régulation.

### Niveaux d'Intensité (Toggle)

- **"Plutôt"** : Correspondance > 0 (Large).
- **"Beaucoup"** : Correspondance > 66% (Strict).
- *Note : Le filtrage par percentiles a été remplacé par un tri par similarité cosinus avec le vecteur cible interpolé.*

### Labels UX
Nous n'affichons jamais les pourcentages bruts à l'utilisateur dans la liste, mais des labels qualitatifs :
- "Correspond beaucoup à ton mood"
- "Correspond bien à ton mood"
- "Correspond un peu à ton mood"

### Fiche Film (`MoodAnalyzerCard`)
Affiche le **Profil Émotionnel** intrinsèque du film :
- Émotion dominante (et son intensité).
- Émotion secondaire (si significative).
- Détection de Dyade (ex: "Mélange de Peur et Surprise = Émerveillement").
