'use client';

import { useRouter, useSearchParams } from 'next/navigation';

// Moods mapped to their IDs (matching config/moods.py)
const MOODS = [
    { id: '', name: 'Toutes les envies' },
    { id: 'adrenaline', name: "Besoin d'adrénaline" },
    { id: 'adventure', name: 'Évasion & Aventure' },
    { id: 'animation', name: 'Un peu de magie' },
    { id: 'comedy', name: 'Besoin de rire' },
    { id: 'crime', name: 'Thriller & Polar' },
    { id: 'documentary', name: 'Apprendre quelque chose' },
    { id: 'drama', name: 'Émotion & Drame' },
    { id: 'family', name: 'En famille' },
    { id: 'fantasy', name: 'Mondes imaginaires' },
    { id: 'history', name: 'Histoire & Passé' },
    { id: 'horror', name: 'Frisson & Horreur' },
    { id: 'music', name: 'Musique & Rythme' },
    { id: 'mystery', name: 'Mystère & Enquête' },
    { id: 'romance', name: 'Amour & Romance' },
    { id: 'scifi', name: 'Futur & SF' },
    { id: 'thriller', name: 'Suspense total' },
    { id: 'war', name: 'Guerre & Conflit' },
    { id: 'western', name: 'Cowboys & Western' },
];

export function GenreMoodFilter() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const currentMood = searchParams.get('mood') || '';

    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const val = e.target.value;
        const params = new URLSearchParams(searchParams.toString());
        if (val) {
            params.set('mood', val);
        } else {
            params.delete('mood');
        }
        params.set('page', '1'); // Reset to page 1
        router.push(`/recommandations?${params.toString()}`);
    };

    return (
        <div className="relative group">
            <label htmlFor="mood-select" className="block text-[8px] font-black uppercase tracking-[0.2em] text-zinc-600 mb-1 ml-1 group-focus-within:text-accent transition-colors">
                Mood / Envie
            </label>
            <div className="relative">
                <select
                    id="mood-select"
                    value={currentMood}
                    onChange={handleChange}
                    className="appearance-none w-full md:w-64 bg-base-200 border border-base-300 rounded-xl px-4 py-2 text-sm font-bold text-white focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all cursor-pointer shadow-inner pr-10"
                >
                    {MOODS.map((mood) => (
                        <option key={mood.id} value={mood.id} className="bg-base-200">
                            {mood.name}
                        </option>
                    ))}
                </select>
                <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-500 group-hover:text-accent transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </div>
            </div>
        </div>
    );
}
