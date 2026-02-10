'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDebounce } from '@/hooks/use-debounce';
import {
    MOOD_NAMES_FR,
    PRIMARY_ORDER,
    getDyadFromPrimaries,
    getAllowedAdjacents,
    moodToPrimaryDistribution,
    type Mood,
    type Preset,
    type PrimaryEmotion
} from '@/lib/mood-scorer';

// Emoji for each mood
const MOOD_EMOJI: Record<Mood, string> = {
    joy: '😊', trust: '🤝', fear: '😨', surprise: '😲',
    sadness: '😢', disgust: '🤢', anger: '😤', anticipation: '🎬',
    love: '❤️', submission: '🙇', awe: '🌟', disapproval: '👎',
    remorse: '😔', contempt: '😒', aggressiveness: '💥', optimism: '🌈',
    ecstasy: '🤩', admiration: '🥹', terror: '😱', amazement: '🤯',
    grief: '💔', loathing: '😖', rage: '🔥', vigilance: '👀',
};

export function GenreMoodFilter() {
    const router = useRouter();
    const searchParams = useSearchParams();

    // URL state
    const currentMood = (searchParams.get('mood') || '') as Mood | '';

    // Local state for immediate UI feedback
    const [localRegulation, setLocalRegulation] = useState<number>(() =>
        parseInt(searchParams.get('regulation') || '0')
    );
    const [localIntensity, setLocalIntensity] = useState<string>(() =>
        searchParams.get('intensity') || 'plutot'
    );

    // Debounce values to avoid flooding URL updates
    const debouncedRegulation = useDebounce(localRegulation, 300);
    const debouncedIntensity = useDebounce(localIntensity, 300);

    // Local selection state (max 2 primaries)
    const [selectedPrimaries, setSelectedPrimaries] = useState<PrimaryEmotion[]>([]);

    // Ref to track if initial mount has happened (to avoid double firing on strict mode)
    const isMounted = useRef(false);

    // Sync local state from URL on mount/update
    useEffect(() => {
        if (!currentMood) {
            setSelectedPrimaries([]);
        } else {
            const dist = moodToPrimaryDistribution(currentMood);
            const primaries = Object.entries(dist)
                .filter(([_, weight]) => weight > 0)
                .map(([mood]) => mood as PrimaryEmotion);
            setSelectedPrimaries(primaries);
        }
    }, [currentMood]);

    // Trigger URL update when debounced values change
    useEffect(() => {
        if (!isMounted.current) {
            isMounted.current = true;
            return;
        }

        // Only update if currentMood exists (toolbar is visible)
        if (currentMood) {
            const params = new URLSearchParams(searchParams.toString());

            // Manage Regulation
            if (debouncedRegulation > 0) {
                params.set('regulation', debouncedRegulation.toString());
            } else {
                params.delete('regulation');
            }

            // Manage Intensity
            if (debouncedIntensity === 'beaucoup') {
                params.set('intensity', 'beaucoup');
            } else {
                params.delete('intensity');
            }

            router.push(`/recommandations?${params.toString()}`, { scroll: false });
        }
    }, [debouncedRegulation, debouncedIntensity, currentMood, router]);
    // Note: searchParams in dependency might cause loops if not careful, but we use debounced values

    const updateMood = (mood: Mood | '') => {
        const params = new URLSearchParams(searchParams.toString());
        if (mood) {
            params.set('mood', mood);
        } else {
            params.delete('mood');
            // Also reset regulation/intensity when clearing mood
            setLocalRegulation(0);
            setLocalIntensity('plutot');
            params.delete('regulation');
            params.delete('intensity');
        }
        params.set('page', '1');
        router.push(`/recommandations?${params.toString()}`);
    };

    const handlePrimaryClick = (mood: PrimaryEmotion) => {
        let newSelection = [...selectedPrimaries];
        if (newSelection.includes(mood)) {
            newSelection = newSelection.filter(m => m !== mood);
        } else {
            if (newSelection.length >= 2) newSelection.shift();
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
            effectiveMood = dyad || p2;
        }

        updateMood(effectiveMood);
    };

    // Colors for each mood
    const MOOD_COLORS: Record<Mood, string> = {
        joy: 'bg-amber-400 text-black border-amber-500 shadow-amber-400/20',
        trust: 'bg-lime-500 text-black border-lime-600 shadow-lime-500/20',
        fear: 'bg-emerald-700 text-white border-emerald-800 shadow-emerald-700/20',
        surprise: 'bg-sky-400 text-black border-sky-500 shadow-sky-400/20',
        sadness: 'bg-indigo-600 text-white border-indigo-700 shadow-indigo-600/20',
        disgust: 'bg-fuchsia-700 text-white border-fuchsia-800 shadow-fuchsia-700/20',
        anger: 'bg-red-600 text-white border-red-700 shadow-red-600/20',
        anticipation: 'bg-orange-500 text-black border-orange-600 shadow-orange-500/20',
        // Dyads
        love: 'bg-gradient-to-br from-amber-400 to-lime-500 text-black',
        submission: 'bg-gradient-to-br from-lime-500 to-emerald-700 text-white',
        awe: 'bg-gradient-to-br from-emerald-700 to-sky-400 text-white',
        disapproval: 'bg-gradient-to-br from-sky-400 to-indigo-600 text-white',
        remorse: 'bg-gradient-to-br from-indigo-600 to-fuchsia-700 text-white',
        contempt: 'bg-gradient-to-br from-fuchsia-700 to-red-600 text-white',
        aggressiveness: 'bg-gradient-to-br from-red-600 to-orange-500 text-white',
        optimism: 'bg-gradient-to-br from-orange-500 to-amber-400 text-black',
        ecstasy: 'bg-amber-300', admiration: 'bg-lime-400', terror: 'bg-emerald-800', amazement: 'bg-sky-300',
        grief: 'bg-indigo-700', loathing: 'bg-fuchsia-800', rage: 'bg-red-700', vigilance: 'bg-orange-400',
    };

    return (
        <div className="flex flex-col gap-8 w-full">
            {/* Header / Prompt */}
            <AnimatePresence>
                {!currentMood && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, height: 0 }}
                        className="text-center space-y-2"
                    >
                        <h2 className="text-2xl font-black text-white uppercase tracking-tighter">
                            Comment vous sentez-vous ?
                        </h2>
                        <p className="text-zinc-500 text-sm font-medium">
                            Sélectionnez une émotion pour commencer, ou combinez-en deux pour plus de précision.
                        </p>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Grid of Emotions */}
            <motion.div
                layout
                className={`grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3`}
            >
                {PRIMARY_ORDER.map((mood) => {
                    const isSelected = selectedPrimaries.includes(mood);

                    let isDisabled = false;
                    let isDimmed = false;

                    if (selectedPrimaries.length === 1 && !isSelected) {
                        const allowed = getAllowedAdjacents(selectedPrimaries[0]!);
                        if (!allowed.includes(mood)) {
                            isDisabled = true;
                            isDimmed = true;
                        }
                    } else if (selectedPrimaries.length === 2 && !isSelected) {
                        isDisabled = true;
                        isDimmed = true;
                    }

                    const baseClasses = "relative h-24 md:h-32 rounded-2xl flex flex-col items-center justify-center gap-2 overflow-hidden border-2 select-none";
                    const colorClass = MOOD_COLORS[mood] || 'bg-zinc-800 border-zinc-700';
                    const stateClasses = isSelected
                        ? `ring-4 ring-white/20 z-10 shadow-xl ${colorClass}`
                        : isDimmed
                            ? 'bg-zinc-900/50 border-zinc-800 text-zinc-600 grayscale opacity-40 cursor-not-allowed'
                            : `bg-zinc-800/80 border-zinc-700 text-zinc-400 cursor-pointer`;

                    const hoverColorClass = !isSelected && !isDimmed
                        ? `hover:${colorClass.split(' ')[0]} hover:border-transparent hover:text-white`
                        : '';

                    return (
                        <motion.button
                            layout
                            key={mood}
                            onClick={() => !isDisabled && handlePrimaryClick(mood)}
                            disabled={isDisabled}
                            whileHover={!isDisabled && !isSelected ? { scale: 1.05 } : {}}
                            whileTap={!isDisabled ? { scale: 0.95 } : {}}
                            animate={{
                                scale: isSelected ? 1.05 : (isDimmed ? 0.95 : 1),
                                opacity: isDimmed ? 0.5 : 1
                            }}
                            className={`${baseClasses} ${stateClasses} ${hoverColorClass}`}
                        >
                            <motion.span
                                className="text-3xl md:text-4xl"
                                animate={{ scale: isSelected ? 1.1 : 1 }}
                            >
                                {MOOD_EMOJI[mood]}
                            </motion.span>
                            <span className="text-[10px] md:text-xs font-black uppercase tracking-widest leading-none">
                                {MOOD_NAMES_FR[mood]}
                            </span>

                            {/* Selection Indicator */}
                            {isSelected && (
                                <motion.div
                                    layoutId="selection-indicator"
                                    className="absolute top-2 right-2 w-2 h-2 bg-white rounded-full shadow-lg"
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    transition={{ type: "spring", stiffness: 500, damping: 30 }}
                                />
                            )}
                        </motion.button>
                    );
                })}
            </motion.div>

            {/* Results Toolbar */}
            <AnimatePresence>
                {currentMood && (
                    <motion.div
                        initial={{ opacity: 0, y: 50, x: "-50%" }}
                        animate={{ opacity: 1, y: 0, x: "-50%" }}
                        exit={{ opacity: 0, y: 50, x: "-50%" }}
                        transition={{ type: "spring", damping: 25, stiffness: 200 }}
                        className="fixed bottom-6 left-1/2 w-full max-w-3xl px-4 z-50"
                    >
                        <div className="bg-zinc-900/90 backdrop-blur-xl border border-white/10 p-4 rounded-3xl shadow-2xl flex flex-col md:flex-row items-center justify-between gap-4 md:gap-8">

                            {/* Selected Mood Display */}
                            <div className="flex items-center gap-4 w-full md:w-auto">
                                <motion.div
                                    layout
                                    className={`w-12 h-12 rounded-2xl flex items-center justify-center text-2xl shadow-lg ${MOOD_COLORS[currentMood as Mood] || 'bg-zinc-800'}`}
                                >
                                    {MOOD_EMOJI[currentMood as Mood]}
                                </motion.div>
                                <div>
                                    <div className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-0.5">Votre Mood</div>
                                    <div className="text-lg font-black text-white uppercase tracking-tight leading-none">
                                        {MOOD_NAMES_FR[currentMood as Mood]}
                                    </div>
                                </div>
                            </div>

                            {/* Mood Regulation Slider */}
                            <div className="flex flex-col w-full md:w-auto gap-3 min-w-[300px]">
                                <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-zinc-500 px-1">
                                    <span>Même Mood</span>
                                    <span>Changer d'air</span>
                                </div>
                                <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    step="1"
                                    value={localRegulation}
                                    onChange={(e) => setLocalRegulation(parseInt(e.target.value))}
                                    className="range range-xs range-accent w-full"
                                />
                                <div className="text-center text-xs font-bold text-white h-4 transition-all opacity-80">
                                    {localRegulation < 33 && "🧘 Rester dans ce mood"}
                                    {localRegulation >= 33 && localRegulation < 66 && "🌈 Adoucir / Nuancer"}
                                    {localRegulation >= 66 && "🚀 Se changer les idées"}
                                </div>
                            </div>

                            {/* Intensity Toggle */}
                            <motion.button
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => setLocalIntensity(current => current === 'beaucoup' ? 'plutot' : 'beaucoup')}
                                className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all border ${localIntensity === 'beaucoup'
                                        ? 'bg-emerald-500/10 border-emerald-500 text-emerald-400'
                                        : 'bg-zinc-800/50 border-white/5 text-zinc-400 hover:text-white'
                                    }`}
                            >
                                <span className="text-[10px] font-black uppercase tracking-widest">Intensité</span>
                                <motion.span
                                    className={`w-3 h-3 rounded-full ${localIntensity === 'beaucoup' ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]' : 'bg-zinc-600'}`}
                                    animate={{ scale: localIntensity === 'beaucoup' ? [1, 1.2, 1] : 1 }}
                                />
                            </motion.button>

                            {/* Clear Button */}
                            <motion.button
                                whileHover={{ scale: 1.1, rotate: 90 }}
                                whileTap={{ scale: 0.9 }}
                                onClick={() => {
                                    setSelectedPrimaries([]);
                                    updateMood('');
                                }}
                                className="w-8 h-8 flex items-center justify-center rounded-full bg-zinc-800 hover:bg-zinc-700 text-zinc-500 hover:text-white transition-colors absolute -top-3 -right-3 md:static md:w-auto md:h-auto md:p-2 md:rounded-xl md:bg-transparent md:hover:bg-white/5"
                                title="Réinitialiser"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </motion.button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
