# Movie Service

> **Objectif** : Centraliser tous les accès aux données films dans un service SSR (Server-Side Rendering) pour l'application Next.js.

---

## 📍 Localisation

```
apps/web/src/services/movie-service.ts
```

---

## 🏗️ Architecture

Le service utilise le pattern **factory** pour créer une instance avec le client Supabase côté serveur :

```typescript
export async function getMovieService() {
    const cookieStore = await cookies()
    const supabase = createClient(cookieStore)
    
    return {
        // méthodes du service
    }
}
```

**Utilisation** :
```typescript
const service = await getMovieService();
const stats = await service.getStats();
```

---

## 🔧 Méthodes

### Dashboard

| Méthode | Return | Description |
|---------|--------|-------------|
| `getStats()` | `{ movies, interactions, candidates }` | Compteurs pour le dashboard |
| `getRecentMovies(limit)` | `Movie[]` | Derniers films importés |
| `getRecentInteractions(limit)` | `Interaction[]` | Dernières notes/actions |
| `getTopCandidates(limit)` | `TasteCandidate[]` | Top recommandations |
| `getRandomRecommendation()` | `TasteCandidate | null` | Recommandation aléatoire |

---

### Page Film

| Méthode | Return | Description |
|---------|--------|-------------|
| `getAIInsight(tmdbId)` | `TasteCandidate | null` | Score Apollo AI pour un film |
| `getInteraction(tmdbId)` | `Interaction | null` | Statut utilisateur (vu, noté, wishlist) |
| `getMoodScoresForMovie(tmdbId)` | `MoodScore[]` | Top 5 moods du film (seuil 15%) |

---

### Page Recommandations

| Méthode | Return | Description |
|---------|--------|-------------|
| `getAllCandidatesPaginated(page, pageSize, moodId?)` | `{ data, count }` | Candidats paginés, filtrables par mood |
| `getAllMoods()` | `{ id, name }[]` | Liste des moods disponibles |

---

## 🎭 Filtrage par Mood

La méthode `getAllCandidatesPaginated` supporte un paramètre optionnel `moodId` :

```typescript
// Sans filtre - top 2000 par taste_score
const { data, count } = await service.getAllCandidatesPaginated(1, 50);

// Avec filtre mood - triés par similarity_score
const { data, count } = await service.getAllCandidatesPaginated(1, 50, 'animation');
```

### Fonctionnement

1. **Avec mood** : Appel RPC `get_candidates_by_mood` (seuil 15%, tri par similarity)
2. **Sans mood** : Query Supabase standard (tri par taste_score)

### Fonctions RPC utilisées

| Fonction | Paramètres | Description |
|----------|------------|-------------|
| `get_candidates_by_mood` | `p_mood_id, p_min_score, p_limit, p_offset` | Récupère candidats filtrés |
| `count_candidates_by_mood` | `p_mood_id, p_min_score` | Compte candidats pour pagination |

---

## 🔄 Hydratation TMDb

Toutes les données sont enrichies avec TMDb en français via `hydrateWithTMDb()` :

```typescript
async function hydrateWithTMDb<T>(items: T[]): Promise<T[]> {
    // Batch de 10 pour éviter saturation API
    // Ajoute: title, poster_path, release_year, overview, genres, is_niche
}
```

**Champs hydratés** :
- `title` : Titre français
- `poster_path` : Affiche
- `release_year` : Année de sortie
- `overview` : Synopsis français
- `genres` : Liste des genres
- `is_niche` : Flag pépite niche

---

## 📊 Types

Définis dans `@/types/database.ts` :

```typescript
interface MoodScore {
    mood_id: string;
    mood_name: string;
    similarity_score: number;
}

interface TasteCandidate {
    id: number;
    tmdb_id: number;
    taste_score: number;
    model_version: string;
    generated_at: string;
    // Joined fields
    title?: string;
    poster_path?: string | null;
    release_year?: number | null;
    overview?: string;
    genres?: string[];
    is_niche?: boolean;
    mood_scores?: MoodScore[];
}
```

---

## 🔗 Dépendances

- `@/utils/supabase/server` : Client Supabase SSR
- `@/lib/tmdb` : API TMDb wrapper
- `next/headers` : Cookies pour auth

---

## 📚 Utilisation par Page

| Page | Méthodes utilisées |
|------|-------------------|
| `/` (Dashboard) | `getStats`, `getRecentMovies`, `getTopCandidates` |
| `/movie/[id]` | `getAIInsight`, `getInteraction`, `getMoodScoresForMovie` |
| `/recommandations` | `getAllCandidatesPaginated` |
