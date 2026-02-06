'use client';

import { MOOD_NAMES_FR, type Mood } from '@/lib/mood-scorer';

interface MoodAnalyzerCardProps {
    primaryEmotion?: string;
    primaryScore?: number;
    secondaryEmotion?: string;
    secondaryScore?: number;
    isDyad?: boolean;
    dyadName?: string;
    isNiche?: boolean;
}

// Emoji for each Plutchik emotion
const EMOTION_EMOJI: Record<string, string> = {
    joy: '😊',
    trust: '🤝',
    fear: '😨',
    surprise: '😲',
    sadness: '😢',
    disgust: '🤢',
    anger: '😤',
    anticipation: '🎬',
    // Dyads
    love: '❤️',
    submission: '🙇',
    awe: '🌟',
    disapproval: '👎',
    remorse: '😔',
    contempt: '😒',
    aggressiveness: '💥',
    optimism: '🌈',
};

// Colors for Plutchik emotions (matching the wheel)
const EMOTION_COLORS: Record<string, { bg: string; text: string; glow: string }> = {
    joy: { bg: 'rgba(250, 204, 21, 0.15)', text: '#facc15', glow: 'rgba(250, 204, 21, 0.3)' },
    trust: { bg: 'rgba(74, 222, 128, 0.15)', text: '#4ade80', glow: 'rgba(74, 222, 128, 0.3)' },
    fear: { bg: 'rgba(34, 197, 94, 0.15)', text: '#22c55e', glow: 'rgba(34, 197, 94, 0.3)' },
    surprise: { bg: 'rgba(6, 182, 212, 0.15)', text: '#06b6d4', glow: 'rgba(6, 182, 212, 0.3)' },
    sadness: { bg: 'rgba(59, 130, 246, 0.15)', text: '#3b82f6', glow: 'rgba(59, 130, 246, 0.3)' },
    disgust: { bg: 'rgba(168, 85, 247, 0.15)', text: '#a855f7', glow: 'rgba(168, 85, 247, 0.3)' },
    anger: { bg: 'rgba(239, 68, 68, 0.15)', text: '#ef4444', glow: 'rgba(239, 68, 68, 0.3)' },
    anticipation: { bg: 'rgba(249, 115, 22, 0.15)', text: '#f97316', glow: 'rgba(249, 115, 22, 0.3)' },
    // Dyads
    love: { bg: 'rgba(244, 114, 182, 0.15)', text: '#f472b6', glow: 'rgba(244, 114, 182, 0.3)' },
    submission: { bg: 'rgba(52, 211, 153, 0.15)', text: '#34d399', glow: 'rgba(52, 211, 153, 0.3)' },
    awe: { bg: 'rgba(20, 184, 166, 0.15)', text: '#14b8a6', glow: 'rgba(20, 184, 166, 0.3)' },
    disapproval: { bg: 'rgba(96, 165, 250, 0.15)', text: '#60a5fa', glow: 'rgba(96, 165, 250, 0.3)' },
    remorse: { bg: 'rgba(129, 140, 248, 0.15)', text: '#818cf8', glow: 'rgba(129, 140, 248, 0.3)' },
    contempt: { bg: 'rgba(192, 132, 252, 0.15)', text: '#c084fc', glow: 'rgba(192, 132, 252, 0.3)' },
    aggressiveness: { bg: 'rgba(251, 146, 60, 0.15)', text: '#fb923c', glow: 'rgba(251, 146, 60, 0.3)' },
    optimism: { bg: 'rgba(253, 186, 116, 0.15)', text: '#fdba74', glow: 'rgba(253, 186, 116, 0.3)' },
};

// Default colors
const DEFAULT_COLORS = { bg: 'rgba(156, 163, 175, 0.15)', text: '#9ca3af', glow: 'rgba(156, 163, 175, 0.3)' };

export function MoodAnalyzerCard({
    primaryEmotion,
    primaryScore,
    secondaryEmotion,
    secondaryScore,
    isDyad,
    dyadName,
    isNiche = false
}: MoodAnalyzerCardProps) {
    // Don't show if no emotion data
    if (!primaryEmotion) {
        return null;
    }

    const primaryColors = EMOTION_COLORS[primaryEmotion] || DEFAULT_COLORS;
    const primaryEmoji = EMOTION_EMOJI[primaryEmotion] || '🎬';
    const primaryName = MOOD_NAMES_FR[primaryEmotion as Mood] || primaryEmotion;

    const secondaryColors = secondaryEmotion ? (EMOTION_COLORS[secondaryEmotion] || DEFAULT_COLORS) : DEFAULT_COLORS;
    const secondaryEmoji = secondaryEmotion ? (EMOTION_EMOJI[secondaryEmotion] || '🎬') : '';
    const secondaryName = secondaryEmotion ? (MOOD_NAMES_FR[secondaryEmotion as Mood] || secondaryEmotion) : '';

    const dyadColors = dyadName ? (EMOTION_COLORS[dyadName] || DEFAULT_COLORS) : DEFAULT_COLORS;
    const dyadEmoji = dyadName ? (EMOTION_EMOJI[dyadName] || '✨') : '';
    const dyadDisplayName = dyadName ? (MOOD_NAMES_FR[dyadName as Mood] || dyadName) : '';

    const accentBorder = isNiche ? 'border-success/30' : 'border-accent/30';
    const shadowClass = isNiche ? 'shadow-success/5' : 'shadow-accent/5';

    // Intensity label based on score
    const getIntensityLabel = (score: number): string => {
        if (score > 0.7) return 'Très intense';
        if (score > 0.4) return 'Marquée';
        return 'Présente';
    };

    return (
        <div className={`bg-base-200 border ${accentBorder} rounded-2xl p-6 space-y-4 relative overflow-hidden group shadow-lg ${shadowClass}`}>
            {/* Background glow */}
            <div
                className="absolute -top-12 -left-12 w-32 h-32 blur-3xl rounded-full"
                style={{ backgroundColor: isDyad ? dyadColors.glow : primaryColors.glow }}
            />

            {/* Header */}
            <div className="flex items-center justify-between relative z-10">
                <h3 className="text-sm font-black text-white uppercase tracking-widest">Profil Émotionnel</h3>
                <div
                    className="px-2 py-0.5 text-[8px] font-black uppercase rounded"
                    style={{ backgroundColor: primaryColors.bg, color: primaryColors.text }}
                >
                    Plutchik
                </div>
            </div>

            {/* Dyad Display (if applicable) */}
            {isDyad && dyadName && (
                <div className="relative z-10 pt-2">
                    <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-2">
                        Dyade détectée
                    </div>
                    <div
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border"
                        style={{
                            backgroundColor: dyadColors.bg,
                            borderColor: `${dyadColors.text}40`,
                            color: dyadColors.text
                        }}
                    >
                        <span className="text-xl">{dyadEmoji}</span>
                        <span className="text-sm font-bold uppercase">{dyadDisplayName}</span>
                    </div>
                    <div className="text-[10px] text-zinc-500 mt-2">
                        Mix de <span style={{ color: primaryColors.text }}>{primaryName}</span> + <span style={{ color: secondaryColors.text }}>{secondaryName}</span>
                    </div>
                </div>
            )}

            {/* Primary Emotion */}
            <div className="relative z-10 pt-2">
                <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">
                    {isDyad ? 'Émotion principale' : 'Émotion dominante'}
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-3xl">{primaryEmoji}</span>
                    <div className="flex flex-col">
                        <span
                            className="text-xl font-black uppercase tracking-tight"
                            style={{ color: primaryColors.text }}
                        >
                            {primaryName}
                        </span>
                        {primaryScore !== undefined && (
                            <span
                                className="text-xs font-bold uppercase tracking-wider"
                                style={{ color: primaryColors.text, opacity: 0.7 }}
                            >
                                {getIntensityLabel(primaryScore)}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            {/* Secondary Emotion */}
            {secondaryEmotion && secondaryScore !== undefined && secondaryScore > 0.15 && (
                <div className="relative z-10">
                    <div className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1">
                        Émotion secondaire
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-xl">{secondaryEmoji}</span>
                        <span
                            className="text-sm font-bold uppercase tracking-tight"
                            style={{ color: secondaryColors.text }}
                        >
                            {secondaryName}
                        </span>
                        <span className="text-xs text-zinc-500">
                            ({getIntensityLabel(secondaryScore)})
                        </span>
                    </div>
                </div>
            )}

            {/* Description */}
            <p className="text-[10px] text-zinc-500 font-medium leading-relaxed relative z-10 pt-1">
                Analyse émotionnelle basée sur le modèle de Plutchik.
            </p>
        </div>
    );
}
