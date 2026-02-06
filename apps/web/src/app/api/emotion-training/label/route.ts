import { NextResponse } from 'next/server';
import { getEmotionTrainingService } from '@/services/emotion-training-service';
import type { PrimaryEmotionDB, LabelKind } from '@/types/database';

interface LabelRequestBody {
    tmdb_id: number;
    emotion: PrimaryEmotionDB;
    label_kind?: LabelKind;
    confidence_self?: 1 | 2 | 3;
}

export async function POST(request: Request) {
    try {
        const body: LabelRequestBody = await request.json();

        if (!body.tmdb_id || !body.emotion) {
            return NextResponse.json(
                { error: 'Missing required fields: tmdb_id, emotion' },
                { status: 400 }
            );
        }

        const validEmotions: PrimaryEmotionDB[] = [
            'joy', 'trust', 'fear', 'surprise',
            'sadness', 'disgust', 'anger', 'anticipation'
        ];

        if (!validEmotions.includes(body.emotion)) {
            return NextResponse.json(
                { error: `Invalid emotion. Must be one of: ${validEmotions.join(', ')}` },
                { status: 400 }
            );
        }

        const service = await getEmotionTrainingService();
        const label = await service.saveLabel(
            body.tmdb_id,
            body.emotion,
            body.label_kind || 'transmitted',
            body.confidence_self
        );

        return NextResponse.json({ success: true, label });
    } catch (error) {
        console.error('Error saving label:', error);
        return NextResponse.json(
            { error: 'Failed to save label' },
            { status: 500 }
        );
    }
}
