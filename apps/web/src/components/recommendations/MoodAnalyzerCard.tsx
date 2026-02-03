'use client';

import { MoodScore } from '@/types/database';
import { formatMoodScore } from '@/utils/mood-format';

interface MoodAnalyzerCardProps {
    moodScores: MoodScore[];
    isNiche?: boolean;
}

// Color palette for mood tags
const MOOD_COLORS: Record<string, { bg: string; text: string; glow: string }> = {
    mind_bending: { bg: 'rgba(168, 85, 247, 0.15)', text: '#a855f7', glow: 'rgba(168, 85, 247, 0.3)' }, // Purple
    feel_good: { bg: 'rgba(250, 204, 21, 0.15)', text: '#facc15', glow: 'rgba(250, 204, 21, 0.3)' },   // Yellow
    dark_gritty: { bg: 'rgba(71, 85, 105, 0.3)', text: '#94a3b8', glow: 'rgba(71, 85, 105, 0.4)' },     // Slate
    tension: { bg: 'rgba(239, 68, 68, 0.15)', text: '#ef4444', glow: 'rgba(239, 68, 68, 0.3)' },       // Red
    surreal: { bg: 'rgba(236, 72, 153, 0.15)', text: '#ec4899', glow: 'rgba(236, 72, 153, 0.3)' },     // Pink
    epic: { bg: 'rgba(249, 115, 22, 0.15)', text: '#f97316', glow: 'rgba(249, 115, 22, 0.3)' },        // Orange
    intimate: { bg: 'rgba(6, 182, 212, 0.15)', text: '#06b6d4', glow: 'rgba(6, 182, 212, 0.3)' },      // Cyan
    nostalgia: { bg: 'rgba(244, 63, 94, 0.15)', text: '#f43f5e', glow: 'rgba(244, 63, 94, 0.3)' },     // Rose
    disturbing: { bg: 'rgba(153, 27, 27, 0.2)', text: '#f87171', glow: 'rgba(153, 27, 27, 0.4)' },     // Dark Red
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
    const matchScore = formatMoodScore(primaryMood.similarity_score);

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
                        {matchScore}
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
                                <span className="opacity-100">
                                    {mood.mood_name}
                                </span>
                                <span className="opacity-70">{formatMoodScore(mood.similarity_score)}</span>
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
