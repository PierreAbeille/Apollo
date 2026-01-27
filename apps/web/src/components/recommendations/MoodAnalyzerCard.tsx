'use client';

import { MoodScore } from '@/types/database';

interface MoodAnalyzerCardProps {
    moodScores: MoodScore[];
    isNiche?: boolean;
}

// Color palette for mood tags
const MOOD_COLORS: Record<string, { bg: string; text: string; glow: string }> = {
    adrenaline: { bg: 'rgba(239, 68, 68, 0.15)', text: '#ef4444', glow: 'rgba(239, 68, 68, 0.3)' },
    adventure: { bg: 'rgba(249, 115, 22, 0.15)', text: '#f97316', glow: 'rgba(249, 115, 22, 0.3)' },
    animation: { bg: 'rgba(168, 85, 247, 0.15)', text: '#a855f7', glow: 'rgba(168, 85, 247, 0.3)' },
    comedy: { bg: 'rgba(250, 204, 21, 0.15)', text: '#facc15', glow: 'rgba(250, 204, 21, 0.3)' },
    crime: { bg: 'rgba(100, 116, 139, 0.15)', text: '#94a3b8', glow: 'rgba(100, 116, 139, 0.3)' },
    documentary: { bg: 'rgba(34, 197, 94, 0.15)', text: '#22c55e', glow: 'rgba(34, 197, 94, 0.3)' },
    drama: { bg: 'rgba(59, 130, 246, 0.15)', text: '#3b82f6', glow: 'rgba(59, 130, 246, 0.3)' },
    family: { bg: 'rgba(244, 114, 182, 0.15)', text: '#f472b6', glow: 'rgba(244, 114, 182, 0.3)' },
    fantasy: { bg: 'rgba(139, 92, 246, 0.15)', text: '#8b5cf6', glow: 'rgba(139, 92, 246, 0.3)' },
    history: { bg: 'rgba(146, 64, 14, 0.15)', text: '#d97706', glow: 'rgba(146, 64, 14, 0.3)' },
    horror: { bg: 'rgba(31, 41, 55, 0.4)', text: '#9ca3af', glow: 'rgba(31, 41, 55, 0.5)' },
    music: { bg: 'rgba(236, 72, 153, 0.15)', text: '#ec4899', glow: 'rgba(236, 72, 153, 0.3)' },
    mystery: { bg: 'rgba(99, 102, 241, 0.15)', text: '#6366f1', glow: 'rgba(99, 102, 241, 0.3)' },
    romance: { bg: 'rgba(244, 63, 94, 0.15)', text: '#f43f5e', glow: 'rgba(244, 63, 94, 0.3)' },
    scifi: { bg: 'rgba(6, 182, 212, 0.15)', text: '#06b6d4', glow: 'rgba(6, 182, 212, 0.3)' },
    thriller: { bg: 'rgba(220, 38, 38, 0.15)', text: '#dc2626', glow: 'rgba(220, 38, 38, 0.3)' },
    war: { bg: 'rgba(120, 113, 108, 0.15)', text: '#a8a29e', glow: 'rgba(120, 113, 108, 0.3)' },
    western: { bg: 'rgba(217, 119, 6, 0.15)', text: '#d97706', glow: 'rgba(217, 119, 6, 0.3)' },
};

export function MoodAnalyzerCard({ moodScores, isNiche = false }: MoodAnalyzerCardProps) {
    if (!moodScores || moodScores.length === 0) {
        return null;
    }

    // Take top 4 moods (first primary, 3 secondary) - no sorting, keep original order
    const primaryMood = moodScores[0];
    if (!primaryMood) {
        return null;
    }
    const secondaryMoods = moodScores.slice(1, 4);

    const primaryColors = MOOD_COLORS[primaryMood.mood_id] || { bg: 'rgba(156, 163, 175, 0.15)', text: '#9ca3af', glow: 'rgba(156, 163, 175, 0.3)' };
    const primaryPercentage = Math.round(primaryMood.similarity_score * 100);

    const accentColor = isNiche ? 'text-success' : 'text-accent';
    const accentBorder = isNiche ? 'border-success/30' : 'border-accent/30';
    const shadowClass = isNiche ? 'shadow-success/5' : 'shadow-accent/5';

    return (
        <div className={`bg-base-200 border ${accentBorder} rounded-2xl p-6 space-y-4 relative overflow-hidden group shadow-lg ${shadowClass}`}>
            {/* Background glow */}
            <div
                className="absolute -top-12 -left-12 w-32 h-32 blur-3xl rounded-full"
                style={{ backgroundColor: primaryColors.glow }}
            />

            {/* Header */}
            <div className="flex items-center justify-between relative z-10">
                <h3 className="text-sm font-black text-white uppercase tracking-widest">Mood Analyzer</h3>
                <div
                    className="px-2 py-0.5 text-[8px] font-black uppercase rounded"
                    style={{ backgroundColor: primaryColors.bg, color: primaryColors.text }}
                >
                    Apollo AI
                </div>
            </div>

            {/* Primary Mood */}
            <div className="pt-2 relative z-10">
                <div className="flex items-center gap-3">
                    <span
                        className="text-3xl font-black tracking-tighter leading-none"
                        style={{ color: primaryColors.text }}
                    >
                        {primaryPercentage}%
                    </span>
                    <div className="flex flex-col">
                        <span
                            className="text-lg font-black uppercase tracking-tight"
                            style={{ color: primaryColors.text }}
                        >
                            {primaryMood.mood_name}
                        </span>
                        <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                            Mood principal
                        </span>
                    </div>
                </div>
            </div>

            {/* Secondary Moods */}
            {secondaryMoods.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-2 relative z-10">
                    {secondaryMoods.map((mood) => {
                        const colors = MOOD_COLORS[mood.mood_id] || { bg: 'rgba(156, 163, 175, 0.15)', text: '#9ca3af', glow: 'rgba(156, 163, 175, 0.3)' };
                        const percentage = Math.round(mood.similarity_score * 100);

                        return (
                            <div
                                key={mood.mood_id}
                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold transition-all hover:scale-105"
                                style={{
                                    backgroundColor: colors.bg,
                                    color: colors.text,
                                    border: `1px solid ${colors.text}30`,
                                }}
                                title={`${mood.mood_name}: ${percentage}%`}
                            >
                                <span className="truncate max-w-[60px]">
                                    {mood.mood_name.split(' ')[0]}
                                </span>
                                <span className="opacity-70">{percentage}%</span>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Description */}
            <p className="text-[10px] text-zinc-500 font-medium leading-relaxed relative z-10 pt-1">
                Analyse sémantique des ambiances et thématiques du film basée sur l'IA Apollo.
            </p>
        </div>
    );
}
