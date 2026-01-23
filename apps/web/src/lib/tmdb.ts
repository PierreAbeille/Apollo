const TMDB_BASE_URL = "https://api.themoviedb.org/3";

interface TMDbConfig {
    apiKey: string | undefined;
    accessToken: string | undefined;
}

const config: TMDbConfig = {
    apiKey: process.env.TMDB_API_KEY,
    accessToken: process.env.TMDB_API_READ_ACCESS_TOKEN,
};

export interface TMDbMovie {
    id: number;
    title: string;
    original_title: string;
    overview: string;
    poster_path: string | null;
    backdrop_path: string | null;
    release_date: string;
    vote_average: number;
    vote_count: number;
    popularity: number;
    runtime: number | null;
    budget: number;
    revenue: number;
    tagline: string | null;
    homepage: string | null;
    genre_ids?: number[];
    genres?: { id: number; name: string }[];
}

export interface TMDbCredits {
    id: number;
    cast: {
        id: number;
        name: string;
        character: string;
        profile_path: string | null;
    }[];
    crew: {
        id: number;
        name: string;
        job: string;
    }[];
}

export interface TMDbSearchResponse {
    page: number;
    results: TMDbMovie[];
    total_pages: number;
    total_results: number;
}

function getHeaders(): HeadersInit {
    if (config.accessToken) {
        return {
            Authorization: `Bearer ${config.accessToken}`,
            "Content-Type": "application/json",
        };
    }
    return {
        "Content-Type": "application/json",
    };
}

function buildUrl(endpoint: string, params?: Record<string, string>): string {
    const url = new URL(`${TMDB_BASE_URL}${endpoint}`);

    // Add API key if using key-based auth
    if (!config.accessToken && config.apiKey) {
        url.searchParams.append("api_key", config.apiKey);
    }

    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            url.searchParams.append(key, value);
        });
    }

    return url.toString();
}

export async function searchMovies(
    query: string,
    page = 1,
    language = "fr-FR"
): Promise<TMDbSearchResponse> {
    const url = buildUrl("/search/movie", {
        query,
        page: String(page),
        language,
        include_adult: "false",
    });

    const response = await fetch(url, {
        headers: getHeaders(),
        next: { revalidate: 3600 }, // Cache for 1 hour
    });

    if (!response.ok) {
        throw new Error(`TMDb API error: ${response.status}`);
    }

    return response.json() as Promise<TMDbSearchResponse>;
}

export async function getPopularMovies(page = 1, language = "fr-FR"): Promise<TMDbSearchResponse> {
    const url = buildUrl("/movie/popular", {
        page: String(page),
        language,
    });

    const response = await fetch(url, {
        headers: getHeaders(),
        next: { revalidate: 3600 },
    });

    if (!response.ok) {
        throw new Error(`TMDb API error: ${response.status}`);
    }

    return response.json() as Promise<TMDbSearchResponse>;
}

export async function getMovieDetails(movieId: number, language = "fr-FR"): Promise<TMDbMovie> {
    const url = buildUrl(`/movie/${movieId}`, {
        language
    });

    const response = await fetch(url, {
        headers: getHeaders(),
        next: { revalidate: 86400 }, // Cache for 24 hours
    });

    if (!response.ok) {
        throw new Error(`TMDb API error: ${response.status}`);
    }

    return response.json() as Promise<TMDbMovie>;
}

export async function getMovieCredits(movieId: number, language = "fr-FR"): Promise<TMDbCredits> {
    const url = buildUrl(`/movie/${movieId}/credits`, {
        language
    });

    const response = await fetch(url, {
        headers: getHeaders(),
        next: { revalidate: 86400 },
    });

    if (!response.ok) {
        throw new Error(`TMDb API error: ${response.status}`);
    }

    return response.json() as Promise<TMDbCredits>;
}

export function getImageUrl(
    path: string | null,
    size: "w92" | "w154" | "w185" | "w342" | "w500" | "w780" | "original" = "w500"
): string | null {
    if (!path) return null;
    return `https://image.tmdb.org/t/p/${size}${path}`;
}
