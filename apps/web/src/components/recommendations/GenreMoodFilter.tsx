'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
    MOOD_NAMES_FR,
    PRESET_NAMES_FR,
    PRIMARY_ORDER,
    getDyadFromPrimaries,
    getAllowedAdjacents,
    moodToPrimaryDistribution,
    isDyad,
    type Mood,
    type Preset,
    type PrimaryEmotion
} from '@/lib/mood-scorer';

// Emoji for each mood
const MOOD_EMOJI: Record<Mood, string> = {
    joy: '😊',
    trust: '🤝',
    fear: '😨',
    surprise: '😲',
    sadness: '😢',
    disgust: '🤢',
    anger: '😤',
    anticipation: '🎬',
    // Primary dyads
    love: '❤️',
    submission: '🙇',
    awe: '🌟',
    disapproval: '👎',
    remorse: '😔',
    contempt: '😒',
    aggressiveness: '💥',
    optimism: '🌈',
    // Intensity dyads
    ecstasy: '🤩',
    admiration: '🥹',
    terror: '😱',
    amazement: '🤯',
    grief: '💔',
    loathing: '😖',
    rage: '🔥',
    vigilance: '👀',
};

const PRESETS: Preset[] = ['congruence', 'regulation', 'stimulation'];

export function GenreMoodFilter() {
    const router = useRouter();
    const searchParams = useSearchParams();

    // URL state
    const currentMood = (searchParams.get('mood') || '') as Mood | '';
    const currentPreset = (searchParams.get('preset') || 'congruence') as Preset;

    // Local selection state (max 2 primaries)
    const [selectedPrimaries, setSelectedPrimaries] = useState<PrimaryEmotion[]>([]);

    // Sync local state from URL on mount
    useEffect(() => {
        if (!currentMood) {
            setSelectedPrimaries([]);
            return;
        }

        const dist = moodToPrimaryDistribution(currentMood);
        const primaries = Object.entries(dist)
            .filter(([_, weight]) => weight > 0)
            .map(([mood]) => mood as PrimaryEmotion);

        setSelectedPrimaries(primaries);
    }, [currentMood]);

    const updateParams = (updates: Record<string, string>) => {
        const params = new URLSearchParams(searchParams.toString());

        Object.entries(updates).forEach(([key, value]) => {
            if (value) {
                params.set(key, value);
            } else {
                params.delete(key);
            }
        });

        params.set('page', '1'); // Reset to page 1
        router.push(`/recommandations?${params.toString()}`);
    };

    const handlePrimaryClick = (mood: PrimaryEmotion) => {
        let newSelection = [...selectedPrimaries];

        if (newSelection.includes(mood)) {
            // Deselect
            newSelection = newSelection.filter(m => m !== mood);
        } else {
            // Select (max 2)
            if (newSelection.length >= 2) {
                // Should not happen if UI is disabled properly, but safety check
                // Remove the first one (FIFO)
                newSelection.shift();
            }
            newSelection.push(mood);
        }

        setSelectedPrimaries(newSelection);

        // Compute effective mood
        let effectiveMood: Mood | '' = '';

        if (newSelection.length === 1) {
            effectiveMood = newSelection[0]!;
        } else if (newSelection.length === 2) {
            const p1 = newSelection[0]!;
            const p2 = newSelection[1]!;
            const dyad = getDyadFromPrimaries(p1, p2);
            effectiveMood = dyad || p2; // Fallback to last selected if no dyad
        }

        updateParams({ mood: effectiveMood });
    };

    const handlePresetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        updateParams({ preset: e.target.value });
    };

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-2">
                <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">
                    Sélectionner 1 ou 2 émotions
                </span>
                <div className="flex flex-wrap gap-2">
                    {PRIMARY_ORDER.map((mood) => {
                        const isSelected = selectedPrimaries.includes(mood);

                        // Check if disabled (must be adjacent to first selection)
                        let isDisabled = false;
                        if (selectedPrimaries.length === 1 && !isSelected) {
                            const allowed = getAllowedAdjacents(selectedPrimaries[0]!);
                            if (!allowed.includes(mood)) isDisabled = true;
                        }

                        // Also disable if we have 2 selected and this is not one modifiers (so user can only deselect)
                        if (selectedPrimaries.length === 2 && !isSelected) {
                            isDisabled = true;
                        }

                        return (
                            <button
                                key={mood}
                                onClick={() => handlePrimaryClick(mood)}
                                disabled={isDisabled}
                                className={`
                                    px-4 py-2 rounded-full text-xs font-bold uppercase tracking-wide transition-all
                                    border flex items-center gap-2
                                    ${isSelected
                                        ? 'bg-accent text-black border-accent shadow-lg shadow-accent/20 scale-105'
                                        : isDisabled
                                            ? 'bg-base-200 text-zinc-700 border-base-200 cursor-not-allowed opacity-50'
                                            : 'bg-base-200 text-zinc-400 border-base-300 hover:border-zinc-500 hover:text-zinc-200'
                                    }
                                `}
                            >
                                <span className={isSelected ? 'grayscale-0' : 'grayscale opacity-70'}>
                                    {MOOD_EMOJI[mood]}
                                </span>
                                {MOOD_NAMES_FR[mood]}
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Results, Preset & Intensity */}
            {currentMood && (
                <div className="flex flex-wrap items-center gap-4 animate-in fade-in slide-in-from-top-2 duration-300">
                    {/* Result Badge */}
                    <div className="flex items-center gap-3 px-4 py-3 bg-base-200 border border-base-300 rounded-xl">
                        <div className="text-[10px] font-black uppercase tracking-widest text-zinc-500">
                            Résultat
                        </div>
                        <div className="w-px h-4 bg-zinc-700"></div>
                        <div className="text-sm font-black text-white uppercase tracking-tight flex items-center gap-2">
                            <span className="text-xl">{MOOD_EMOJI[currentMood]}</span>
                            {MOOD_NAMES_FR[currentMood]}
                            {isDyad(currentMood) && <span className="text-[10px] text-accent ml-1 bg-accent/10 px-1.5 py-0.5 rounded border border-accent/20">Mix</span>}
                        </div>
                    </div>

                    {/* Arrow */}
                    <div className="text-zinc-600">→</div>

                    {/* Preset Selector */}
                    <div className="relative group">
                        <select
                            id="preset-select"
                            value={currentPreset}
                            onChange={handlePresetChange}
                            className="appearance-none w-full md:w-52 bg-base-200 border border-base-300 rounded-xl px-4 py-3 text-sm font-bold text-white focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all cursor-pointer shadow-inner pr-10"
                        >
                            {PRESETS.map((preset) => (
                                <option key={preset} value={preset} className="bg-base-200">
                                    {preset === 'congruence' && '🎯 '}
                                    {preset === 'regulation' && '🌈 '}
                                    {preset === 'stimulation' && '⚡ '}
                                    {PRESET_NAMES_FR[preset]}
                                </option>
                            ))}
                        </select>
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-500 group-hover:text-accent transition-colors">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </div>
                    </div>

                    {/* Arrow */}
                    <div className="text-zinc-600">→</div>

                    {/* Intensity Selector */}
                    <div className="flex items-center gap-2 px-4 py-2 bg-base-200 border border-base-300 rounded-xl">
                        <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500">Intensité</span>
                        <div className="flex gap-1">
                            <button
                                onClick={() => updateParams({ intensity: 'plutot' })}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${searchParams.get('intensity') !== 'beaucoup'
                                    ? 'bg-accent text-black'
                                    : 'bg-base-300 text-zinc-400 hover:text-zinc-200'
                                    }`}
                            >
                                Plutôt
                            </button>
                            <button
                                onClick={() => updateParams({ intensity: 'beaucoup' })}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${searchParams.get('intensity') === 'beaucoup'
                                    ? 'bg-emerald-500 text-black'
                                    : 'bg-base-300 text-zinc-400 hover:text-zinc-200'
                                    }`}
                            >
                                Beaucoup
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
