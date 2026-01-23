'use client';

import { useRouter, useSearchParams } from 'next/navigation';

const MOOD_GENRES = [
    { id: '', name: 'Toutes les envies' },
    { id: 'Action', name: 'Besoin d\'adrénaline' },
    { id: 'Adventure', name: 'Évasion & Aventure' },
    { id: 'Animation', name: 'Un peu de magie' },
    { id: 'Comedy', name: 'Besoin de rire' },
    { id: 'Crime', name: 'Thriller & Polar' },
    { id: 'Documentary', name: 'Apprendre quelque chose' },
    { id: 'Drama', name: 'Émotion & Drame' },
    { id: 'Family', name: 'En famille' },
    { id: 'Fantasy', name: 'Mondes imaginaires' },
    { id: 'History', name: 'Histoire & Passé' },
    { id: 'Horror', name: 'Frisson & Horreur' },
    { id: 'Music', name: 'Musique & Rythme' },
    { id: 'Mystery', name: 'Mystère & Enquête' },
    { id: 'Romance', name: 'Amour & Romance' },
    { id: 'Science Fiction', name: 'Futur & SF' },
    { id: 'Thriller', name: 'Suspense total' },
    { id: 'War', name: 'Guerre & Conflit' },
    { id: 'Western', name: 'Cowboys & Western' },
];

export function GenreMoodFilter() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const currentGenre = searchParams.get('genre') || '';

    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const val = e.target.value;
        const params = new URLSearchParams(searchParams.toString());
        if (val) {
            params.set('genre', val);
        } else {
            params.delete('genre');
        }
        params.set('page', '1'); // Reset to page 1
        router.push(`/recommandations?${params.toString()}`);
    };

    return (
        <div className="relative group">
            <label htmlFor="mood-select" className="block text-[8px] font-black uppercase tracking-[0.2em] text-zinc-600 mb-1 ml-1 group-focus-within:text-accent transition-colors">
                Mood / Genre
            </label>
            <div className="relative">
                <select
                    id="mood-select"
                    value={currentGenre}
                    onChange={handleChange}
                    className="appearance-none w-full md:w-64 bg-base-200 border border-base-300 rounded-xl px-4 py-2 text-sm font-bold text-white focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/20 transition-all cursor-pointer shadow-inner pr-10"
                >
                    {MOOD_GENRES.map((mood) => (
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
