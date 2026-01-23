import { createClient } from '@/utils/supabase/server'
import { cookies } from 'next/headers'
import { Movie, Interaction, TasteCandidate } from '@/types/database'
import { getMovieDetails } from '@/lib/tmdb'

export async function getMovieService() {
    const cookieStore = await cookies()
    const supabase = createClient(cookieStore)

    /**
     * Helper to hydrate database results with French TMDb content
     */
    async function hydrateWithTMDb<T extends { tmdb_id: number }>(items: T[]): Promise<T[]> {
        return Promise.all(
            items.map(async (item) => {
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
                    };
                } catch (e) {
                    console.error(`Failed to hydrate movie ${item.tmdb_id}:`, e);
                    return item;
                }
            })
        );
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
        }
    }
}
