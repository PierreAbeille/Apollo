'use server';

import { getMovieService } from '@/services/movie-service';
import { Movie } from '@/types/database';

export async function searchMoviesAction(query: string): Promise<Movie[]> {
    if (!query || query.length < 2) return [];

    const movieService = await getMovieService();
    return movieService.searchMoviesInLibrary(query);
}
