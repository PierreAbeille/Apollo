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
| `getAllCandidatesPaginated(page, pageSize, moodId?, regulation?, intensity?)` | `{ data, count }` | Candidats paginés, filtrables par mood + regulation |
| `getAllMoods()` | `{ id, name }[]` | Liste des moods disponibles |

---

## 🎭 Filtrage par Mood

La méthode `getAllCandidatesPaginated` supporte désormais la régulation émotionnelle :

```typescript
// Sans filtre
const { data, count } = await service.getAllCandidatesPaginated(1, 50);

// Avec filtre mood simple (Congruence)
const { data, count } = await service.getAllCandidatesPaginated(1, 50, 'joy', 0, 'plutot');

// Avec régulation (Antidote - ex: Sadness -> Joy)
const { data, count } = await service.getAllCandidatesPaginated(1, 50, 'sadness', 100, 'beaucoup');
```

### Fonctionnement V2 (Client-Side Logic)

Contrairement à la V1 (RPC), la V2 utilise un fichier JSON statique (`movie_emotions.json`) chargés en mémoire serveur :

1.  **Chargement** : Le service charge `movie_emotions.json` (map tmdb_id -> vector).
2.  **Filtrage** : 
    - Calcule le vecteur cible (Target) basé sur le mood sélectionné et le slider de régulation (interpolation linéaire).
    - Calcule la similarité cosinus entre chaque film candidat et le vecteur cible.
3.  **Tri** : Réordonne les candidats par ce nouveau score de similarité.
4.  **Pagination** : Renvoie la page demandée.

*Note : Les RPC `get_candidates_by_mood` sont dépréciées en faveur de cette approche "stateless" et plus flexible.*

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
