# Architecture Web Apollo

> **Vue d'ensemble de l'application Next.js et de ses optimisations.**

---

## 🏗️ Stack Technique

- **Framework** : Next.js 16.1.1 (App Router)
- **TypeScript** : 5+ (strict mode)
- **Styles** : Tailwind CSS 4
- **Backend** : Supabase (PostgreSQL + API REST)
- **API Externe** : TMDb (The Movie Database)
- **Déploiement** : Compatible Vercel, Netlify, etc.

---

## 📁 Structure du Projet

```
apps/web/
├── src/
│   ├── app/                    # Routes Next.js (App Router)
│   │   ├── layout.tsx          # Layout global
│   │   ├── page.tsx            # Dashboard (/)
│   │   ├── movie/              
│   │   │   └── [id]/page.tsx   # Détails film (/movie/123)
│   │   └── recommandations/
│   │       └── page.tsx        # Liste complète (/recommandations)
│   ├── components/             # Composants React
│   │   ├── dashboard/
│   │   │   ├── TopCandidates.tsx
│   │   │   ├── StatsGrid.tsx
│   │   │   └── RandomRecommendation.tsx
│   │   └── recommendations/
│   │       └── GenreMoodFilter.tsx
│   ├── services/               # Logique métier
│   │   └── movie-service.ts    # Service Supabase
│   ├── lib/                    # Utilitaires
│   │   └── tmdb.ts             # Client TMDb API
│   ├── types/                  # Types TypeScript
│   │   └── database.ts         # Interfaces DB
│   └── utils/                  # Helpers
│       └── supabase/           # Clients Supabase SSR
├── package.json
└── tailwind.config.ts
```

---

## 🌐 Routes et Pages

### Dashboard (`/`)

**Fichier** : `src/app/page.tsx`

**Responsabilités** :
- Afficher statistiques globales (films, interactions, candidats)
- Top 5 recommandations avec cartes visuelles
- Recommandation aléatoire ("Lucky Pick")

**Data Fetching** : Server Component (SSR)

**APIs appelées** :
```typescript
const service = await getMovieService();
const stats = await service.getStats();
const topCandidates = await service.getTopCandidates(5);
```

---

### Détails Film (`/movie/[id]`)

**Fichier** : `src/app/movie/[id]/page.tsx`

**Responsabilités** :
- Afficher poster, synopsis, année, genres
- AI Insights (score de match, badge Batch v1)
- Détection "niche" avec thème vert dynamique
- Statut utilisateur (wishlist, vu, note)

**Thème Dynamique** :
```typescript
const isNiche = !!movie.is_niche;
const accentColor = isNiche ? 'text-success' : 'text-accent';
const accentBg = isNiche ? 'bg-success/10' : 'bg-accent/10';
```

**Data Fetching** : 
- Movie metadata : Supabase (`getMovieById`)
- TMDb hydration : `getMovieDetails(id, 'fr-FR')`
- Interaction : Supabase (`getInteraction`)

---

### Liste Complète (`/recommandations`)

**Fichier** : `src/app/recommandations/page.tsx`

**Responsabilités** :
- Table paginée (50 films/page)
- Filtrage par genre/mood (dropdown)
- Batch processing optimisé (DB-first)

**Paramètres URL** :
- `?page=2` : Pagination
- `?genre=Action` : Filtrage

**Optimisations** :
```typescript
// 1. Fetch depuis DB avec join
const { data } = await supabase
    .from('taste_candidates')
    .select(`
        *,
        movies (
            title, 
            poster_path, 
            release_year,
            movie_features (genres, overview)
        )
    `)
    .limit(1000);  // Fetch large pour filtrage en mémoire

// 2. Filtrer en JS (rapide)
let candidates = data.filter(c => 
    c.movies.movie_features.genres.some(g => g.name === genre)
);

// 3. Paginer
const paginated = candidates.slice(from, to);

// 4. Hydratation TMDb (seulement les 50 visibles)
const hydrated = await hydrateWithTMDb(paginated);
```

---

## 🔌 Intégrations API

### Supabase (PostgreSQL)

**Setup** :
```typescript
// src/utils/supabase/server.ts
import { createServerClient } from '@supabase/ssr';

export function createClient(cookieStore) {
    return createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY!,
        {
            cookies: {
                get: (name) => cookieStore.get(name)?.value,
                set: (name, value, options) => cookieStore.set(name, value, options),
                remove: (name, options) => cookieStore.delete(name, options),
            },
        }
    );
}
```

**Usage** :
```typescript
const service = await getMovieService();
const { data } = await service.getAllCandidatesPaginated(1, 50, 'Action');
```

---

### TMDb API

**Client** : `src/lib/tmdb.ts`

**Optimisations** :
1. **Batching** : Max 10 requêtes parallèles
2. **Fallback langue** : `fr-FR` → `en-US` si synopsis vide
3. **Niche detection** : Calcul côté client

**Code** :
```typescript
export async function getMovieDetails(tmdbId: number, language: string) {
    const res = await fetch(
        `https://api.themoviedb.org/3/movie/${tmdbId}?language=${language}`,
        {
            headers: {
                Authorization: `Bearer ${process.env.TMDB_API_READ_ACCESS_TOKEN}`,
            },
        }
    );
    
    let data = await res.json();
    
    // Fallback si synopsis vide
    if (!data.overview && language !== 'en-US') {
        data = await getMovieDetails(tmdbId, 'en-US');
    }
    
    // Calcul niche
    data.is_niche = (data.popularity < 30 && data.vote_count < 5000) || 
                    (data.vote_count < 1000);
    
    return data;
}
```

---

## 🎨 Design System

### Couleurs

**Palette** :
```css
/* Tailwind config */
colors: {
    base: {
        100: '#0f0f0f',  /* Background */
        200: '#1a1a1a',  /* Cards */
        300: '#262626',  /* Borders */
    },
    accent: '#f59e0b',    /* Jaune (mainstream) */
    success: '#10b981',   /* Vert (niche) */
}
```

**Usage** :
```tsx
<div className={`bg-${isNiche ? 'success' : 'accent'}/10`}>
```

---

### Composants Réutilisables

#### `TopCandidates`

```tsx
interface TopCandidatesProps {
    candidates: TasteCandidate[];
}

export function TopCandidates({ candidates }: TopCandidatesProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {candidates.map(candidate => (
                <RecommendationCard key={candidate.tmdb_id} candidate={candidate} />
            ))}
        </div>
    );
}
```

#### `GenreMoodFilter`

```tsx
'use client';  // Client component

export function GenreMoodFilter() {
    const router = useRouter();
    const searchParams = useSearchParams();
    
    const handleChange = (genre: string) => {
        const params = new URLSearchParams(searchParams);
        params.set('genre', genre);
        params.set('page', '1');  // Reset pagination
        router.push(`/recommandations?${params}`);
    };
    
    return <select onChange={(e) => handleChange(e.target.value)}>...</select>;
}
```

---

## ⚡ Optimisations Performance

### 1. DB-First Filtering

**Problème** : Appeler TMDb pour 1000 films juste pour filtrer = lent + quota.

**Solution** : Fetch genres depuis `movie_features` (DB), filtrer en mémoire, puis hydrater seulement la page visible.

```typescript
// ❌ Mauvais : Hydrate tout puis filtre
const all = await hydrateWithTMDb(candidates);  // 1000 API calls !
const filtered = all.filter(c => c.genres.includes('Action'));

// ✅ Bon : Filtre d'abord, hydrate après
const preFiltered = candidates.filter(c => 
    c.movies.movie_features.genres.some(g => g.name === 'Action')
);
const hydrated = await hydrateWithTMDb(preFiltered.slice(0, 50));  // 50 API calls
```

---

### 2. Batch TMDb Calls

```typescript
async function hydrateWithTMDb<T extends { tmdb_id: number }>(items: T[]): Promise<T[]> {
    const batchSize = 10;
    const results: T[] = [];
    
    for (let i = 0; i < items.length; i += batchSize) {
        const batch = items.slice(i, i + batchSize);
        const batchResults = await Promise.all(
            batch.map(item => getMovieDetails(item.tmdb_id, 'fr-FR'))
        );
        results.push(...batchResults);
    }
    
    return results;
}
```

**Avantage** : Limite les requêtes concurrentes (évite saturation réseau).

---

### 3. Server Components par Défaut

**Next.js 16** : Tous les composants sont Server Components sauf si `'use client'`.

**Avantages** :
- Moins de JavaScript envoyé au client
- Data fetching côté serveur (pas d'API route nécessaire)
- SEO automatique

**Exemple** :
```tsx
// ✅ Server Component (par défaut)
async function DashboardPage() {
    const service = await getMovieService();
    const stats = await service.getStats();
    return <StatsGrid stats={stats} />;
}

// ❌ Client Component (seulement si nécessaire)
'use client';
function GenreMoodFilter() {
    const router = useRouter();  // Hooks React → Client
    ...
}
```

---

## 🛡️ Type Safety

### Interfaces TypeScript

**Fichier** : `src/types/database.ts`

```typescript
export interface TasteCandidate {
    id: number;
    tmdb_id: number;
    taste_score: number;  // 0.0 - 1.0
    model_version: string;
    generated_at: string;
    // Champs hydratés (optionnels)
    title?: string;
    genres?: string[];
    is_niche?: boolean;
}
```

**Validation** :
```typescript
// ✅ Type-safe
const candidates: TasteCandidate[] = await service.getTopCandidates(10);
const score = candidates[0].taste_score;  // number garanti

// ❌ Erreur de compilation
const wrong: TasteCandidate = { taste_score: "high" };  // Type error !
```

---

## 📱 Responsive Design

**Breakpoints Tailwind** :
- `sm:` : 640px+
- `md:` : 768px+
- `lg:` : 1024px+

**Exemple** :
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {/* Mobile: 1 colonne, Tablet: 2, Desktop: 3 */}
</div>
```

---

## 🔐 Sécurité

### Variables d'Environnement

```bash
# .env.local (jamais committé)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY=eyJ...
TMDB_API_KEY=abc123...
TMDB_API_READ_ACCESS_TOKEN=eyJ...
```

**`NEXT_PUBLIC_*`** : Exposé au client (OK pour URLs publiques)  
**Sans prefix** : Privé côté serveur uniquement

---

## 🧪 Testing (Future)

**Recommandations** :
- **Unit** : Vitest pour services
- **Integration** : Playwright pour pages
- **E2E** : Tests de bout en bout (login → browse → details)

---

## 📚 Ressources

- **[Next.js App Router Docs](https://nextjs.org/docs/app)**
- **[Supabase JS Client](https://supabase.com/docs/reference/javascript)**
- **[Tailwind CSS](https://tailwindcss.com/docs)**

---

**Voir aussi** :
- [Contrats d'Interface](../guidelines/interface-contracts.md)
- [Contrats de Données](../guidelines/data-contracts.md)
