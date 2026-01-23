'use server';

import { getMovieService } from './movie-service';

export async function getRandomMovieAction() {
    const service = await getMovieService();
    return service.getRandomRecommendation();
}
