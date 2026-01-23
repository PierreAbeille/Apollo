import { createClient } from '@/utils/supabase/server'
import { cookies } from 'next/headers'
import { Movie, Interaction, TasteCandidate } from '@/types/database'
import { getMovieDetails } from '@/lib/tmdb'

export async function getMovieService() {
    const cookieStore = await cookies()
    const supabase = createClient(cookieStore)

    /**
     * Helper to hydrate database results with French TMDb content
     * Uses batching to prevent saturating the network/API
     */
    async function hydrateWithTMDb<T extends { tmdb_id: number }>(items: T[]): Promise<T[]> {
        const batchSize = 10;
        const results: T[] = [];

        for (let i = 0; i < items.length; i += batchSize) {
            const batch = items.slice(i, i + batchSize);
            const batchResults = await Promise.all(
                batch.map(async (item) => {
                    try {
                        const tmdbData = await getMovieDetails(item.tmdb_id, 'fr-FR');
                        return {
                            ...item,
                            title: tmdbData.title,
                            poster_path: tmdbData.poster_path,
                            release_year: tmdbData.release_date ? parseInt(tmdbData.release_date.substring(0, 4)) : null,
                            overview: tmdbData.overview,
                            genres: tmdbData.genres?.map(g => g.name) || [],
                            is_niche: tmdbData.is_niche,
                        } as T;
                    } catch (e) {
                        console.error(`Failed to hydrate movie ${item.tmdb_id}:`, e);
                        return item;
                    }
                })
            );
            results.push(...batchResults);
        }

        return results;
    }

    return {
        async getStats() {
            const [movies, interactions, candidates] = await Promise.all([
                supabase.from('movies').select('*', { count: 'exact', head: true }),
                supabase.from('interactions').select('*', { count: 'exact', head: true }),
                supabase.from('taste_candidates').select('*', { count: 'exact', head: true }),
            ])

            return {
                movies: movies.count ?? 0,
                interactions: interactions.count ?? 0,
                candidates: candidates.count ?? 0,
            }
        },

        async getRecentMovies(limit = 5): Promise<Movie[]> {
            const { data, error } = await supabase
                .from('movies')
                .select('*')
                .order('updated_at', { ascending: false })
                .limit(limit)

            if (error) throw error
            return hydrateWithTMDb(data || []);
        },

        async getRecentInteractions(limit = 5): Promise<(Interaction & { title?: string })[]> {
            const { data, error } = await supabase
                .from('interactions')
                .select('*')
                .order('created_at', { ascending: false })
                .limit(limit)

            if (error) throw error
            return hydrateWithTMDb(data || []);
        },

        async getTopCandidates(limit = 5): Promise<TasteCandidate[]> {
            const { data, error } = await supabase
                .from('taste_candidates')
                .select('*, movies!inner(tmdb_id)') // Just get the ID to fetch from TMDB after
                .order('taste_score', { ascending: false })
                .limit(limit)

            if (error) throw error

            return hydrateWithTMDb(data || []);
        },

        async getRandomRecommendation(): Promise<TasteCandidate | null> {
            // First get count
            const { count, error: countError } = await supabase
                .from('taste_candidates')
                .select('*', { count: 'exact', head: true });

            if (countError || !count) return null;

            const randomIndex = Math.floor(Math.random() * count);

            const { data, error } = await supabase
                .from('taste_candidates')
                .select('*')
                .range(randomIndex, randomIndex)
                .single();

            if (error || !data) return null;

            const hydrated = await hydrateWithTMDb([data]);
            return hydrated[0];
        },

        async getAIInsight(tmdbId: number): Promise<TasteCandidate | null> {
            const { data, error } = await supabase
                .from('taste_candidates')
                .select('*')
                .eq('tmdb_id', tmdbId)
                .maybeSingle();

            if (error || !data) return null;
            return data;
        },

        async getInteraction(tmdbId: number): Promise<Interaction | null> {
            const { data, error } = await supabase
                .from('interactions')
                .select('*')
                .eq('tmdb_id', tmdbId)
                .maybeSingle();

            if (error || !data) return null;
            return data;
        },

        async getAllCandidatesPaginated(page = 1, pageSize = 50, genre?: string): Promise<{ data: TasteCandidate[], count: number }> {
            const from = (page - 1) * pageSize;
            const to = from + pageSize - 1;

            // 1. Fetch joined data from DB to avoid TMDb calls during screening/filtering
            // We fetch up to 1000 items to perform filtering on top candidates
            const { data, error } = await supabase
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
                .order('taste_score', { ascending: false })
                .limit(genre ? 1000 : 500);

            if (error) throw error;

            // 2. Map and Filter results using DB data
            let candidates: TasteCandidate[] = (data || []).map((item: any) => {
                const movies = item.movies;
                // Supabase returns joined rows as arrays for 1-to-many relationships
                const features = Array.isArray(movies?.movie_features)
                    ? movies.movie_features[0]
                    : movies?.movie_features;

                return {
                    ...item,
                    title: movies?.title || item.title,
                    poster_path: movies?.poster_path || item.poster_path,
                    release_year: movies?.release_year || item.release_year,
                    // DB genres are objects [{id, name}], mapped to string array
                    genres: features?.genres?.map((g: any) => g.name) || [],
                    overview: features?.overview || item.overview
                };
            });

            if (genre) {
                candidates = candidates.filter(c =>
                    c.genres?.some(g => g.toLowerCase() === genre.toLowerCase())
                );
            }

            // 3. Pagination slice
            const paginatedItems = candidates.slice(from, to + 1);
            const totalCount = genre ? candidates.length : 2000;

            // 4. Batch-hydrate ONLY the results for the current page
            // This ensures we have the latest French data and niche detection
            const hydrated = await hydrateWithTMDb(paginatedItems);

            return {
                data: hydrated,
                count: totalCount
            };
        }
    }
}
