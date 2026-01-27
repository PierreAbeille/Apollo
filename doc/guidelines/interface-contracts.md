# Contrats d'Interface Apollo

Ce document définit les APIs internes (services, clients) et les contrats de composants pour garantir la cohérence du système.

---

## 🎬 Movie Service API

Localisé dans `apps/web/src/services/movie-service.ts`.

### `getMovieService()`

Factory fonction qui retourne un objet service avec les méthodes suivantes.

**Usage** :
```typescript
import { getMovieService } from '@/services/movie-service';

const service = await getMovieService();
const stats = await service.getStats();
```

---

### Méthodes

#### `getStats(): Promise<DatabaseStats>`

Récupère les statistiques globales du dashboard.

**Retour** :
```typescript
interface DatabaseStats {
    totalMovies: number;        // Nombre total dans movies table
    totalInteractions: number;  // Nombre total d'interactions
    totalCandidates: number;    // Nombre de recommandations
}
```

**Exemple** :
```typescript
const stats = await service.getStats();
console.log(`${stats.totalCandidates} films analysés`);
```

---

#### `getTopCandidates(limit: number): Promise<TasteCandidate[]>`

Récupère les N meilleures recommandations avec hydratation TMDb.

**Paramètres** :
- `limit` : Nombre de résultats (défaut: 5)

**Retour** : Array de `TasteCandidate` avec champs hydratés (`title`, `poster_path`, `genres`, `is_niche`, etc.)

**Comportement** :
1. Fetch depuis `taste_candidates` (ordre par `taste_score DESC`)
2. Batch hydration via TMDb (batches de 10)
3. Calcul de `is_niche` basé sur popularité/votes TMDb

**Exemple** :
```typescript
const topFilms = await service.getTopCandidates(10);
```

---

#### `getAllCandidatesPaginated(page: number, pageSize: number, genre?: string): Promise<{ data: TasteCandidate[], count: number }>`

Récupère les recommandations paginées avec filtrage optionnel par genre.

**Paramètres** :
- `page` : Numéro de page (1-indexed)
- `pageSize` : Nombre de résultats par page (typiquement 50)
- `genre` : (Optionnel) Nom du genre en anglais (ex: `"Action"`, `"Thriller"`)

**Retour** :
```typescript
{
    data: TasteCandidate[],  // Films de la page courante (hydratés)
    count: number            // Nombre total de résultats (pour pagination)
}
```

**Optimisations** :
- **DB-first** : Join `movie_features` pour récupérer `genres` directement
- **Filtrage en mémoire** : Appliqué avant pagination pour éviter appels TMDb inutiles
- **Hydratation ciblée** : Seulement les 50 films de la page sont hydratés via TMDb

**Exemple** :
```typescript
// Page 1, filtrer par Action
const { data, count } = await service.getAllCandidatesPaginated(1, 50, 'Action');
const totalPages = Math.ceil(count / 50);
```

---

#### `getMovieById(tmdbId: number): Promise<Movie | null>`

Récupère un film depuis la table `movies`.

**Paramètres** :
- `tmdbId` : Identifiant TMDb

**Retour** : Objet `Movie` ou `null` si introuvable

**Exemple** :
```typescript
const movie = await service.getMovieById(550); // Fight Club
```

---

#### `getInteraction(tmdbId: number): Promise<Interaction | null>`

Récupère l'interaction utilisateur pour un film.

**Paramètres** :
- `tmdbId` : Identifiant TMDb

**Retour** : Objet `Interaction` ou `null` si aucune interaction

**Exemple** :
```typescript
const interaction = await service.getInteraction(550);
if (interaction?.is_wishlisted) {
    console.log('Film dans la wishlist');
}
```

---

## 🌐 TMDb Client API

Localisé dans `apps/web/src/lib/tmdb.ts`.

### `getMovieDetails(tmdbId: number, language: string): Promise<TMDbMovieDetails>`

Récupère les détails complets d'un film depuis TMDb avec calcul de `is_niche`.

**Paramètres** :
- `tmdbId` : Identifiant TMDb
- `language` : Code langue (ex: `'fr-FR'`, `'en-US'`)

**Retour** :
```typescript
interface TMDbMovieDetails {
    id: number;
    title: string;
    overview: string;          // Peut être vide si pas de traduction
    release_date: string;      // Format ISO "YYYY-MM-DD"
    poster_path: string | null;
    backdrop_path: string | null;
    genres: Array<{ id: number; name: string }>;
    vote_average: number;
    vote_count: number;
    popularity: number;
    is_niche: boolean;         // Calculé par Apollo (pas TMDb)
    // ... autres champs TMDb standard
}
```

**Logique `is_niche`** :
```typescript
const isNiche = (data.popularity < 30 && data.vote_count < 5000) ||
                (data.vote_count < 1000);
```

**Fallback Langue** :
Si `overview` est vide pour la langue demandée, un second appel est fait en `en-US`.

**Rate Limiting** :
- **Limite** : 50 requêtes/seconde (TMDb)
- **Gestion** : Batching (voir `hydrateWithTMDb`)

**Exemple** :
```typescript
import { getMovieDetails } from '@/lib/tmdb';

const film = await getMovieDetails(550, 'fr-FR');
console.log(film.is_niche ? 'Pépite!' : 'Mainstream');
```

---

### `getImageUrl(path: string | null, size: string): string | null`

Génère l'URL complète d'une image TMDb.

**Paramètres** :
- `path` : Chemin relatif (ex: `/abc123.jpg`)
- `size` : Taille de l'image (ex: `'w500'`, `'w92'`, `'original'`)

**Retour** : URL complète ou `null` si `path` est null

**Exemple** :
```typescript
const posterUrl = getImageUrl(movie.poster_path, 'w500');
// → "https://image.tmdb.org/t/p/w500/abc123.jpg"
```

---

## 🐍 Python Database Client API

Localisé dans `apps/ml/clients/db.py`.

### `DatabaseClient` (Context Manager)

**Usage** :
```python
from clients.db import DatabaseClient

with DatabaseClient() as db:
    movies = db.fetch_all("SELECT * FROM movies LIMIT 10")
```

### Méthodes Principales

#### `upsert_movie(tmdb_id, title, release_year, poster_path)`

Insère ou met à jour un film.

**Paramètres** :
- `tmdb_id` : int
- `title` : str
- `release_year` : int | None
- `poster_path` : str | None

**Comportement** : `ON CONFLICT (tmdb_id) DO UPDATE`

---

#### `upsert_movie_features(tmdb_id, lang, overview, keywords, genres, cast, crew, text_for_embedding)`

Insère ou met à jour les features ML.

**Paramètres** :
- `tmdb_id` : int
- `lang` : `'en'` | `'fr'`
- `overview` : str
- `keywords` : list[dict] (format TMDb)
- `genres` : list[dict]
- `cast` : list[dict]
- `crew` : list[dict]
- `text_for_embedding` : str (construit via `features/text_builder.py`)

---

#### `insert_taste_candidates(candidates: list, model_version: str)`

Insère les recommandations calculées.

**Paramètres** :
- `candidates` : list[tuple[int, float]] (tmdb_id, score)
- `model_version` : str (ex: `"paraphrase-multilingual-MiniLM-L12-v2_v2"`)

**Comportement** : Efface la table avant insertion (`clear_taste_candidates()` appelé avant)

---

## 🎨 Contrats de Composants React

### `TopCandidates`

Localisé dans `apps/web/src/components/dashboard/TopCandidates.tsx`.

**Props** :
```typescript
interface TopCandidatesProps {
    candidates: TasteCandidate[];
}
```

**Responsabilités** :
- Afficher les top recommandations en grille
- Lien "Voir tout →" vers `/recommandations`
- Thème dynamique (vert pour `is_niche`)

---

### `GenreMoodFilter`

Localisé dans `apps/web/src/components/recommendations/GenreMoodFilter.tsx`.

**Props** : Aucun (utilise `useSearchParams()`)

**Responsabilités** :
- Dropdown de sélection de genre/mood
- Mise à jour du paramètre `?genre=` dans l'URL
- Reset de la page à 1 lors du changement

**Données** :
```typescript
const MOOD_GENRES = [
    { id: 'all', label: 'Tous les moods' },
    { id: 'Action', label: 'Besoin d\'adrénaline' },
    { id: 'Romance', label: 'Envie d\'amour' },
    // ... IDs = noms anglais TMDb
];
```

**Contrainte** : Doit être wrappé dans `<Suspense>` car client component utilisant `useSearchParams`.

---

### `RandomRecommendation`

Localisé dans `apps/web/src/components/dashboard/RandomRecommendation.tsx`.

**Props** :
```typescript
interface RandomRecommendationProps {
    candidate: TasteCandidate;
}
```

**Responsabilités** :
- Afficher une carte "lucky pick"
- Générer un nouveau film aléatoire au clic
- Redirection vers `/movie/[id]`

---

## 🔌 Hooks Personnalisés (Future)

*Pas encore implémentés - réservés pour réutilisabilité.*

### `useMovieDetails(tmdbId: number)`

```typescript
function useMovieDetails(tmdbId: number) {
    const [movie, setMovie] = useState<TMDbMovieDetails | null>(null);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        getMovieDetails(tmdbId, 'fr-FR').then(setMovie).finally(() => setLoading(false));
    }, [tmdbId]);
    
    return { movie, loading };
}
```

---

## 🛡️ Gestion d'Erreurs

### Backend (Next.js Server Actions)

```typescript
try {
    const service = await getMovieService();
    const candidates = await service.getTopCandidates(10);
} catch (error) {
    console.error('Failed to fetch candidates:', error);
    // Retourner un fallback ou relancer
}
```

### Frontend (Composants)

```typescript
if (!candidates || candidates.length === 0) {
    return <div>Aucune recommandation disponible</div>;
}
```

---

## 📐 Type Safety

### Supabase Types

Utiliser les types générés par Supabase CLI (recommandé) :

```bash
npx supabase gen types typescript --project-id <project-id> > src/types/supabase.ts
```

### Assertions de Type

Éviter `as` sauf si absolument nécessaire :

```typescript
// ❌ Mauvais
const data = response as TasteCandidate[];

// ✅ Bon
const data: TasteCandidate[] = response;
```

---

## 📚 Ressources

- [Next.js Server Actions](https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions)
- [Supabase JS Client](https://supabase.com/docs/reference/javascript/introduction)
- [TMDb API Docs](https://developers.themoviedb.org/3)
