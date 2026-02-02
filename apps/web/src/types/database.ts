export interface Movie {
    tmdb_id: number;
    title: string;
    release_year: number | null;
    poster_path: string | null;
    updated_at: string;
}

export interface Interaction {
    id: number;
    tmdb_id: number;
    rating: number | null;
    is_done: boolean;
    is_wishlisted: boolean;
    is_recommended: boolean;
    source: string;
    created_at: string;
}

export interface MoodScore {
    mood_id: string;
    mood_name: string;
    similarity_score: number;
}

export interface TasteCandidate {
    id: number;
    tmdb_id: number;
    taste_score: number;
    taste_score_formatted?: string;
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

