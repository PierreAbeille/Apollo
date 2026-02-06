import { createClient } from '@/utils/supabase/server';
import { cookies } from 'next/headers';
import type {
    MovieToLabel,
    MovieEmotionLabel,
    PrimaryEmotionDB,
    LabelKind,
    EmotionTrainingProgress
} from '@/types/database';

export async function getEmotionTrainingService() {
    const cookieStore = await cookies();
    const supabase = createClient(cookieStore);

    return {
        /**
         * Get list of watched movies for labeling.
         * @param seed - Stable random seed for shuffle
         * @param unlabeledOnly - Filter to only unlabeled movies
         */
        async getMoviesToLabel(seed: number = 42, unlabeledOnly: boolean = true): Promise<MovieToLabel[]> {
            // Get watched movies with their interactions
            let query = supabase
                .from('interactions')
                .select(`
                    tmdb_id,
                    rating,
                    review_text,
                    movies!inner (
                        title,
                        release_year,
                        poster_path,
                        movie_features (
                            overview
                        )
                    )
                `)
                .eq('is_done', true);

            const { data: interactions, error } = await query;
            if (error) throw error;

            console.log('Interactions loaded:', interactions?.length);

            // Get already labeled movies
            const { data: labels } = await supabase
                .from('movie_emotion_labels')
                .select('tmdb_id')
                .eq('label_kind', 'transmitted');

            const labeledTmdbIds = new Set((labels || []).map(l => l.tmdb_id));

            // Transform and filter
            let movies: MovieToLabel[] = (interactions || []).map((i: Record<string, unknown>) => {
                const movie = i.movies as Record<string, unknown>;
                const featuresUnsafe = movie?.movie_features;
                // Safe access to nested features array or object (Supabase returns array for 1:N but typically 1:1 if defined right)
                const features = Array.isArray(featuresUnsafe) ? featuresUnsafe[0] : featuresUnsafe as Record<string, unknown> | null;

                return {
                    tmdb_id: i.tmdb_id as number,
                    title: movie?.title as string || 'Unknown',
                    release_year: movie?.release_year as number | null,
                    poster_path: movie?.poster_path as string | null,
                    rating: i.rating as number | null,
                    review_text: i.review_text as string | null,
                    overview: features?.overview as string | null,
                    is_labeled: labeledTmdbIds.has(i.tmdb_id as number),
                };
            });

            if (unlabeledOnly) {
                movies = movies.filter(m => !m.is_labeled);
            }

            // Deterministic shuffle using seed
            movies = seededShuffle(movies, seed);

            return movies;
        },

        /**
         * Save an emotion label for a movie.
         */
        async saveLabel(
            tmdbId: number,
            emotion: PrimaryEmotionDB,
            labelKind: LabelKind = 'transmitted',
            confidenceSelf?: 1 | 2 | 3
        ): Promise<MovieEmotionLabel> {
            const { data, error } = await supabase
                .from('movie_emotion_labels')
                .upsert({
                    tmdb_id: tmdbId,
                    emotion,
                    label_kind: labelKind,
                    confidence_self: confidenceSelf || null,
                    source: 'emotion-training-ui',
                    updated_at: new Date().toISOString(),
                }, {
                    onConflict: 'tmdb_id,label_kind',
                })
                .select()
                .single();

            if (error) throw error;
            return data as MovieEmotionLabel;
        },

        /**
         * Undo the last label (delete most recent).
         */
        async undoLastLabel(): Promise<{ tmdb_id: number } | null> {
            // Get last label
            const { data: lastLabel } = await supabase
                .from('movie_emotion_labels')
                .select('id, tmdb_id')
                .order('created_at', { ascending: false })
                .limit(1)
                .single();

            if (!lastLabel) return null;

            // Delete it
            const { error } = await supabase
                .from('movie_emotion_labels')
                .delete()
                .eq('id', lastLabel.id);

            if (error) throw error;

            return { tmdb_id: lastLabel.tmdb_id };
        },

        /**
         * Get labeling progress stats.
         */
        async getProgress(): Promise<EmotionTrainingProgress> {
            // Total watched movies
            const { count: total } = await supabase
                .from('interactions')
                .select('*', { count: 'exact', head: true })
                .eq('is_done', true);

            // Labeled movies
            const { count: labeled } = await supabase
                .from('movie_emotion_labels')
                .select('*', { count: 'exact', head: true })
                .eq('label_kind', 'transmitted');

            return {
                total: total || 0,
                labeled: labeled || 0,
                remaining: (total || 0) - (labeled || 0),
            };
        },
    };
}

/**
 * Seeded shuffle for deterministic random ordering.
 */
function seededShuffle<T>(array: T[], seed: number): T[] {
    const result = [...array];
    let m = result.length;
    let s = seed;

    while (m) {
        // Simple LCG for seeded random
        s = (s * 1103515245 + 12345) & 0x7fffffff;
        const i = s % m--;
        // Manual swap with type assertions because TS doesn't trust index access
        const t = result[m] as T;
        result[m] = result[i] as T;
        result[i] = t;
    }

    return result;
}
