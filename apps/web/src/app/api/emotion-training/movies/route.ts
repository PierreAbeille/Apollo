import { NextResponse } from 'next/server';
import { getEmotionTrainingService } from '@/services/emotion-training-service';

export async function GET(request: Request) {
    try {
        const { searchParams } = new URL(request.url);
        const seed = parseInt(searchParams.get('seed') || '42');
        const unlabeledOnly = searchParams.get('unlabeled') !== 'false';

        const service = await getEmotionTrainingService();
        const movies = await service.getMoviesToLabel(seed, unlabeledOnly);

        return NextResponse.json({ movies });
    } catch (error) {
        console.error('Error fetching movies to label:', error);
        return NextResponse.json(
            { error: 'Failed to fetch movies' },
            { status: 500 }
        );
    }
}
