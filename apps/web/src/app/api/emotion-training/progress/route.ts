import { NextResponse } from 'next/server';
import { getEmotionTrainingService } from '@/services/emotion-training-service';

export async function GET() {
    try {
        const service = await getEmotionTrainingService();
        const progress = await service.getProgress();

        return NextResponse.json(progress);
    } catch (error) {
        console.error('Error fetching progress:', error);
        return NextResponse.json(
            { error: 'Failed to fetch progress' },
            { status: 500 }
        );
    }
}
