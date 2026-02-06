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

## Algorithme de Filtrage (Percentiles)

Pour éviter les seuils arbitraires (ex: "score > 0.5"), nous utilisons une approche relative basée sur les **percentiles**.

### Problème résolu
Un film d'horreur peut avoir un score de "Peur" de 0.9, alors qu'une comédie dramatique peut avoir un score de "Tristesse" max à 0.4. Comparer ces scores bruts est difficile.

### Solution
Pour chaque requête :
1. On calcule le score de compatibilité (Mood Score) de chaque film du Top 300 avec l'émotion demandée.
2. On classe ces 300 films du moins pertinent au plus pertinent.
3. On assigne un **rang percentile** à chaque film (0 à 100).
   - Le film le plus pertinent du lot a un percentile de 100.
   - Le film médian a un percentile de 50.

### Niveaux d'Intensité

L'utilisateur peut choisir l'intensité du filtre :
- **"Plutôt"** : Garde les films du **Top 66%** (Percentile ≥ 33). Plus permissif.
- **"Beaucoup"** : Garde les films du **Top 33%** (Percentile ≥ 66). Plus strict.

## Interface Utilisateur

### Sélecteur d'Émotions (`GenreMoodFilter`)
- Permet de choisir 1 ou 2 émotions primaires.
- Si 2 émotions adjacentes sont choisies, l'interface indique la Dyade correspondante (ex: "Amour").
- **Presets** :
  - *Congruence* : Cherche des films correspondant à l'émotion sélectionnée.
  - *Régulation* : Cherche l'émotion opposée pour équilibrer (ex: Tristesse -> Joie).

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
