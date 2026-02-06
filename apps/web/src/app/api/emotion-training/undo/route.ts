import { NextResponse } from 'next/server';
import { getEmotionTrainingService } from '@/services/emotion-training-service';

export async function POST() {
    try {
        const service = await getEmotionTrainingService();
        const result = await service.undoLastLabel();

        if (!result) {
            return NextResponse.json(
                { undone: false, message: 'No label to undo' },
                { status: 404 }
            );
        }

        return NextResponse.json({ undone: true, tmdb_id: result.tmdb_id });
    } catch (error) {
        console.error('Error undoing label:', error);
        return NextResponse.json(
            { error: 'Failed to undo label' },
            { status: 500 }
        );
    }
}
