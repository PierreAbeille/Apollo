import { createClient } from '@/utils/supabase/server'
import { cookies } from 'next/headers'
import { Movie, Interaction, TasteCandidate, MoodScore } from '@/types/database'
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

        async getAllCandidatesPaginated(page = 1, pageSize = 50, moodId?: string): Promise<{ data: TasteCandidate[], count: number }> {
            const from = (page - 1) * pageSize;

            // If mood is selected, we filter and sort by mood similarity score
            if (moodId) {
                // Get count first
                const { data: countResult, error: countError } = await supabase
                    .rpc('count_candidates_by_mood', {
                        p_mood_id: moodId,
                        p_min_score: 0.15
                    });

                if (countError) throw countError;

                // Get paginated results using RPC
                const { data, error } = await supabase
                    .rpc('get_candidates_by_mood', {
                        p_mood_id: moodId,
                        p_min_score: 0.15,
                        p_limit: pageSize,
                        p_offset: from
                    });

                if (error) throw error;

                // Map RPC results to TasteCandidate format
                const candidates: TasteCandidate[] = (data || []).map((item: any) => ({
                    id: item.id,
                    tmdb_id: item.tmdb_id,
                    taste_score: item.taste_score,
                    model_version: item.model_version,
                    generated_at: item.generated_at,
                    title: item.title,
                    poster_path: item.poster_path,
                    release_year: item.release_year,
                    mood_scores: [{
                        mood_id: moodId,
                        mood_name: moodId,
                        similarity_score: item.similarity_score
                    }]
                }));

                // Batch-hydrate the page
                const hydrated = await hydrateWithTMDb(candidates);

                return {
                    data: hydrated,
                    count: countResult || 0
                };
            }

            // No mood filter - original behavior
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
                .range(from, from + pageSize - 1);

            if (error) throw error;

            // Map results
            let candidates: TasteCandidate[] = (data || []).map((item: any) => {
                const movies = item.movies;
                const features = Array.isArray(movies?.movie_features)
                    ? movies.movie_features[0]
                    : movies?.movie_features;

                return {
                    ...item,
                    title: movies?.title || item.title,
                    poster_path: movies?.poster_path || item.poster_path,
                    release_year: movies?.release_year || item.release_year,
                    genres: features?.genres?.map((g: any) => g.name) || [],
                    overview: features?.overview || item.overview
                };
            });

            // Batch-hydrate the page
            const hydrated = await hydrateWithTMDb(candidates);

            return {
                data: hydrated,
                count: 2000  // Total candidates
            };
        },

        async getMoodScoresForMovie(tmdbId: number): Promise<MoodScore[]> {
            const { data, error } = await supabase
                .from('movie_mood_scores')
                .select(`
                    mood_id,
                    similarity_score,
                    moods (name)
                `)
                .eq('tmdb_id', tmdbId)
                .gte('similarity_score', 0.15)
                .order('similarity_score', { ascending: false })
                .limit(5);

            if (error) throw error;

            return (data || []).map((item: any) => ({
                mood_id: item.mood_id,
                mood_name: item.moods?.name || item.mood_id,
                similarity_score: item.similarity_score
            }));
        },

        async getAllMoods(): Promise<{ id: string; name: string }[]> {
            const { data, error } = await supabase
                .from('moods')
                .select('id, name')
                .order('name');

            if (error) throw error;
            return data || [];
        }
    }
}
