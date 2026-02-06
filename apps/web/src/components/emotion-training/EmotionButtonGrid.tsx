'use client';

import type { PrimaryEmotionDB } from '@/types/database';
import { MOOD_NAMES_FR, PRIMARY_ORDER, type PrimaryEmotion } from '@/lib/mood-scorer';

interface EmotionButtonGridProps {
    onSelect: (emotion: PrimaryEmotionDB) => void;
    disabled?: boolean;
}

// Emoji and colors for each emotion
const EMOTION_CONFIG: Record<PrimaryEmotion, { emoji: string; color: string; bgColor: string; description: string }> = {
    joy: {
        emoji: '😊',
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-500/20 border-yellow-500/30 hover:bg-yellow-500/30',
        description: 'Sentiment de bonheur, de légèreté, de plaisir. Le film fait sourire ou rire.'
    },
    trust: {
        emoji: '🤝',
        color: 'text-green-400',
        bgColor: 'bg-green-500/20 border-green-500/30 hover:bg-green-500/30',
        description: 'Sentiment de sécurité, de réconfort. On se sent en confiance avec les personnages.'
    },
    fear: {
        emoji: '😨',
        color: 'text-emerald-400',
        bgColor: 'bg-emerald-500/20 border-emerald-500/30 hover:bg-emerald-500/30',
        description: 'Tension, angoisse, sentiment d\'insécurité. Le film met mal à l\'aise.'
    },
    surprise: {
        emoji: '😲',
        color: 'text-cyan-400',
        bgColor: 'bg-cyan-500/20 border-cyan-500/30 hover:bg-cyan-500/30',
        description: 'Rebondissements, twists inattendus. Le film surprend et déroute.'
    },
    sadness: {
        emoji: '😢',
        color: 'text-blue-400',
        bgColor: 'bg-blue-500/20 border-blue-500/30 hover:bg-blue-500/30',
        description: 'Mélancolie, émotion lourde, moments déchirants. Le film touche profondément.'
    },
    disgust: {
        emoji: '🤢',
        color: 'text-purple-400',
        bgColor: 'bg-purple-500/20 border-purple-500/30 hover:bg-purple-500/30',
        description: 'Malaise viscéral ou moral. Quelque chose de repoussant ou dérangeant.'
    },
    anger: {
        emoji: '😤',
        color: 'text-red-400',
        bgColor: 'bg-red-500/20 border-red-500/30 hover:bg-red-500/30',
        description: 'Frustration, injustice, tension explosive. Le film fait bouillir.'
    },
    anticipation: {
        emoji: '🎬',
        color: 'text-orange-400',
        bgColor: 'bg-orange-500/20 border-orange-500/30 hover:bg-orange-500/30',
        description: 'Excitation, suspense, envie de savoir la suite. Le film captive.'
    },
};

// Keyboard shortcuts (1-8)
const SHORTCUTS = ['1', '2', '3', '4', '5', '6', '7', '8'];

export function EmotionButtonGrid({ onSelect, disabled = false }: EmotionButtonGridProps) {
    return (
        <div className="space-y-3">
            <h3 className="text-xs font-black text-zinc-400 uppercase tracking-widest">
                Ce film transmet surtout…
            </h3>

            <div className="grid grid-cols-2 gap-2">
                {PRIMARY_ORDER.map((emotion, index) => {
                    const config = EMOTION_CONFIG[emotion];
                    const frenchName = MOOD_NAMES_FR[emotion];

                    return (
                        <div key={emotion} className="relative group">
                            <button
                                onClick={() => onSelect(emotion as PrimaryEmotionDB)}
                                disabled={disabled}
                                className={`
                                    w-full flex items-center gap-3 px-4 py-3 
                                    rounded-xl border transition-all duration-200
                                    ${config.bgColor}
                                    ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer active:scale-95'}
                                `}
                            >
                                <span className="text-2xl">{config.emoji}</span>
                                <div className="flex-1 text-left">
                                    <span className={`text-sm font-bold ${config.color}`}>
                                        {frenchName}
                                    </span>
                                </div>
                                <span className="text-xs font-mono text-zinc-500 bg-base-300/50 px-1.5 py-0.5 rounded">
                                    {SHORTCUTS[index]}
                                </span>
                            </button>

                            {/* Tooltip */}
                            <div className="
                                absolute left-1/2 -translate-x-1/2 bottom-full mb-2 
                                w-64 p-3 rounded-lg bg-base-300 border border-zinc-700
                                text-xs text-zinc-300 shadow-xl
                                opacity-0 invisible group-hover:opacity-100 group-hover:visible
                                transition-all duration-200 z-50
                                pointer-events-none
                            ">
                                <div className="flex items-center gap-2 mb-1">
                                    <span>{config.emoji}</span>
                                    <span className={`font-bold ${config.color}`}>{frenchName}</span>
                                </div>
                                <p className="text-zinc-400 leading-relaxed">{config.description}</p>
                                <div className="absolute left-1/2 -translate-x-1/2 top-full w-2 h-2 bg-base-300 border-r border-b border-zinc-700 transform rotate-45 -mt-1"></div>
                            </div>
                        </div>
                    );
                })}
            </div>

            <p className="text-[10px] text-zinc-500 text-center">
                💡 Appuie sur <span className="font-mono">1-8</span> pour labelliser rapidement
            </p>
        </div>
    );
}
