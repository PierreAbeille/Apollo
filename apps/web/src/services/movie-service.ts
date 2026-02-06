import { createClient } from '@/utils/supabase/server'
import { cookies } from 'next/headers'
import { Movie, Interaction, TasteCandidate, MoodScore } from '@/types/database'
import { getMovieDetails, searchMovies } from '@/lib/tmdb'
import { formatTasteScore } from '@/utils/format'
import {
    rerankWithMood,
    getDominantEmotion,
    getDyadFromPrimaries,
    PRIMARY_ORDER,
    MOOD_NAMES_FR,
    MOOD_MATCH_LABELS,
    type EmotionData,
    type Mood,
    type Preset,
    type MoodIntensity
} from '@/lib/mood-scorer'
import { readFile } from 'fs/promises'
import { join } from 'path'

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

            const hydrated = await hydrateWithTMDb(data || []);
            return hydrated.map(item => ({
                ...item,
                taste_score_formatted: formatTasteScore(item.taste_score)
            }));
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
            const candidate = hydrated[0];
            return {
                ...candidate,
                taste_score_formatted: formatTasteScore(candidate.taste_score)
            };
        },

        async getAIInsight(tmdbId: number): Promise<TasteCandidate | null> {
            const { data, error } = await supabase
                .from('taste_candidates')
                .select('*')
                .eq('tmdb_id', tmdbId)
                .maybeSingle();

            if (error || !data) return null;
            return {
                ...data,
                taste_score_formatted: formatTasteScore(data.taste_score)
            };
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

        async getAllCandidatesPaginated(
            page = 1,
            pageSize = 50,
            moodId?: string,
            preset: Preset = 'congruence',
            intensity: MoodIntensity = 'plutot'
        ): Promise<{ data: TasteCandidate[], count: number }> {
            const from = (page - 1) * pageSize;

            // If mood is selected, use Plutchik-based reranking
            if (moodId) {
                // Load all candidates (we need full list for reranking)
                const { data: allData, error: allError } = await supabase
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
                    .limit(300); // Top 300 for subtle reordering to match user preference

                if (allError) throw allError;

                // Load emotion data from JSON
                let emotionData: EmotionData = {};
                try {
                    const emotionPath = join(process.cwd(), 'public', 'data', 'movie_emotions.json');
                    const emotionJson = await readFile(emotionPath, 'utf-8');
                    emotionData = JSON.parse(emotionJson);
                } catch (e) {
                    console.warn('Could not load emotion data:', e);
                }

                // Map to candidates with taste_score
                const candidates = (allData || []).map((item: any) => {
                    const movies = item.movies;
                    const features = Array.isArray(movies?.movie_features)
                        ? movies.movie_features[0]
                        : movies?.movie_features;

                    return {
                        ...item,
                        tmdb_id: item.tmdb_id,
                        taste_score: item.taste_score,
                        title: movies?.title || item.title,
                        poster_path: movies?.poster_path || item.poster_path,
                        release_year: movies?.release_year || item.release_year,
                        genres: features?.genres?.map((g: any) => g.name) || [],
                        overview: features?.overview || item.overview,
                        taste_score_formatted: formatTasteScore(item.taste_score)
                    };
                });

                // Rerank and filter by mood percentile
                const mood = moodId as Mood;
                const reranked = rerankWithMood(candidates, emotionData, mood, preset, intensity);

                // Paginate
                const paged = reranked.slice(from, from + pageSize);

                // Add mood info for display
                const finalCandidates: TasteCandidate[] = paged.map((c) => {
                    const emotions = emotionData[c.tmdb_id.toString()];
                    const dominant = emotions ? getDominantEmotion(emotions.e) : null;

                    return {
                        ...c,
                        taste_score_formatted: formatTasteScore(c.taste_score),
                        mood_scores: [{
                            mood_id: moodId,
                            mood_name: MOOD_NAMES_FR[mood],
                            similarity_score: c.mood_score
                        }],
                        mood_label: c.mood_label,
                        mood_label_text: MOOD_MATCH_LABELS[c.mood_label as keyof typeof MOOD_MATCH_LABELS],
                        mood_percentile: c.mood_percentile,
                        dominant_emotion: dominant?.emotion,
                        dominant_emotion_score: dominant?.score
                    } as TasteCandidate;
                });

                // Hydrate with TMDb
                const hydrated = await hydrateWithTMDb(finalCandidates);

                return {
                    data: hydrated,
                    count: reranked.length
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
                    overview: features?.overview || item.overview,
                    taste_score_formatted: formatTasteScore(item.taste_score)
                };
            });

            // Batch-hydrate the page
            const hydrated = await hydrateWithTMDb(candidates);

            return {
                data: hydrated,
                count: 2000  // Total candidates
            };
        },

        async getPlutchikEmotionsForMovie(tmdbId: number): Promise<{
            emotions: number[];
            confidence: number;
            primaryEmotion: string;
            primaryScore: number;
            secondaryEmotion: string;
            secondaryScore: number;
            isDyad: boolean;
            dyadName?: string;
        } | null> {
            try {
                const emotionPath = join(process.cwd(), 'public', 'data', 'movie_emotions.json');
                const emotionJson = await readFile(emotionPath, 'utf-8');
                const emotionData: EmotionData = JSON.parse(emotionJson);

                const movieEmotions = emotionData[tmdbId.toString()];
                if (!movieEmotions) return null;

                // Get top 2 emotions
                const emotionScores = movieEmotions.e.map((score, idx) => ({
                    emotion: PRIMARY_ORDER[idx],
                    score
                })).sort((a, b) => b.score - a.score);

                const primary = emotionScores[0];
                const secondary = emotionScores[1];

                // Check if they form a dyad (adjacent emotions)
                let isDyad = false;
                let dyadName: string | undefined;

                if (primary?.emotion && secondary?.emotion && secondary.score > 0.2) {
                    const dyad = getDyadFromPrimaries(primary.emotion, secondary.emotion);
                    if (dyad) {
                        isDyad = true;
                        dyadName = dyad;
                    }
                }

                return {
                    emotions: movieEmotions.e,
                    confidence: movieEmotions.c,
                    primaryEmotion: primary?.emotion || 'joy',
                    primaryScore: primary?.score || 0,
                    secondaryEmotion: secondary?.emotion || 'trust',
                    secondaryScore: secondary?.score || 0,
                    isDyad,
                    dyadName
                };
            } catch (e) {
                console.warn('Could not load emotion data for movie:', tmdbId, e);
                return null;
            }
        },

        async getAllMoods(): Promise<{ id: string; name: string }[]> {
            const { data, error } = await supabase
                .from('moods')
                .select('id, name')
                .order('name');

            if (error) throw error;
            return data || [];
        },

        async searchMoviesInLibrary(query: string): Promise<Movie[]> {
            // 1. Search by ID (if query is a number)
            let idMatch: Movie | null = null;
            if (!isNaN(Number(query))) {
                const { data } = await supabase
                    .from('movies')
                    .select('*')
                    .eq('tmdb_id', query)
                    .maybeSingle();
                if (data) idMatch = data;
            }

            // 2. Search by Title in DB
            const terms = query.trim().split(/\s+/).filter(t => t.length > 0);
            let titleQuery = supabase.from('movies').select('*');

            terms.forEach(term => {
                titleQuery = titleQuery.ilike('title', `%${term}%`);
            });

            const { data: titleMatches } = await titleQuery.limit(20);

            // 3. Search in TMDb
            let tmdbMatchesInDb: Movie[] = [];
            try {
                const tmdbResults = await searchMovies(query);
                if (tmdbResults.results.length > 0) {
                    const tmdbIds = tmdbResults.results.map(m => m.id);
                    const { data } = await supabase
                        .from('movies')
                        .select('*')
                        .in('tmdb_id', tmdbIds);
                    if (data) tmdbMatchesInDb = data;
                }
            } catch (error) {
                console.error('TMDb search failed:', error);
            }

            // Combine and Deduplicate
            const allMatches = [
                ...(idMatch ? [idMatch] : []),
                ...(titleMatches || []),
                ...tmdbMatchesInDb
            ];

            const uniqueMatches = Array.from(
                new Map(allMatches.map(item => [item.tmdb_id, item])).values()
            );

            return hydrateWithTMDb(uniqueMatches);
        }
    }
}
