'use client';

import type { EmotionTrainingProgress as ProgressData } from '@/types/database';

interface TrainingProgressProps {
    progress: ProgressData;
    currentIndex: number;
}

export function TrainingProgress({ progress, currentIndex }: TrainingProgressProps) {
    const percentage = progress.total > 0
        ? Math.round((progress.labeled / progress.total) * 100)
        : 0;

    return (
        <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-zinc-400 uppercase tracking-widest">
                    Progression
                </span>
                <span className="font-mono text-zinc-300">
                    {currentIndex + 1} / {progress.remaining + progress.labeled}
                </span>
            </div>

            {/* Progress bar */}
            <div className="h-2 bg-base-300 rounded-full overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-accent to-success transition-all duration-300"
                    style={{ width: `${percentage}%` }}
                />
            </div>

            {/* Stats */}
            <div className="flex items-center justify-between text-[10px] text-zinc-500">
                <span>{progress.labeled} labellisés</span>
                <span className="text-accent font-bold">{progress.remaining} restants</span>
            </div>
        </div>
    );
}
