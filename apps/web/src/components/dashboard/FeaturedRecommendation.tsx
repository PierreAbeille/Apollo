'use client';

import { TasteCandidate } from '@/types/database';
import { getRandomMovieAction } from '@/services/actions';
import { useState } from 'react';

export function FeaturedRecommendation({ initialCandidate }: { initialCandidate: TasteCandidate | null }) {
    const [candidate, setCandidate] = useState<TasteCandidate | null>(initialCandidate);
    const [isLoading, setIsLoading] = useState(false);

    if (!candidate) return null;

    const handleRefresh = async () => {
        setIsLoading(true);
        try {
            const next = await getRandomMovieAction();
            if (next) setCandidate(next);
        } catch (e) {
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="md:col-span-2 bg-base-200 border border-base-300 rounded-xl overflow-hidden shadow-lg group">
            <div className="relative flex flex-col md:flex-row h-full">
                {/* Background Poster Blur */}
                <div
                    className="absolute inset-0 opacity-10 blur-3xl pointer-events-none scale-150"
                    style={{
                        backgroundImage: candidate.poster_path ? `url(https://image.tmdb.org/t/p/w342${candidate.poster_path})` : '',
                        backgroundSize: 'cover',
                        backgroundPosition: 'center'
                    }}
                />

                {/* Poster - Fixed to take full height and remove padding */}
                <div className="relative z-10 w-full md:w-48 h-72 md:h-auto flex-shrink-0 bg-base-300 overflow-hidden">
                    {candidate.poster_path ? (
                        <img
                            src={`https://image.tmdb.org/t/p/w342${candidate.poster_path}`}
                            alt={candidate.title}
                            className="w-full h-full object-cover shadow-2xl transition-transform duration-700 group-hover:scale-105"
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center text-zinc-600 font-black uppercase text-xs">
                            Pas d'affiche
                        </div>
                    )}
                    <div className="absolute top-4 left-4 bg-accent text-accent-content text-[9px] font-black px-2 py-1 rounded-md shadow-xl uppercase tracking-widest">
                        À la une
                    </div>
                </div>

                {/* Content */}
                <div className="relative z-10 flex-1 p-6 flex flex-col justify-between">
                    <div className={isLoading ? 'opacity-50 transition-opacity' : 'transition-opacity'}>
                        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
                            <div>
                                <h3 className="text-2xl font-black text-white tracking-tight leading-none mb-1">
                                    {candidate.title}
                                </h3>
                                <p className="text-zinc-500 text-sm font-bold uppercase tracking-tighter">
                                    {candidate.release_year || 'S.A'}
                                </p>
                            </div>
                            <div className="flex flex-col items-end">
                                <div className="text-3xl font-black text-accent tracking-tighter">
                                    {(candidate.taste_score * 100).toFixed(0)}%
                                </div>
                                <div className="text-[10px] text-zinc-600 font-black uppercase tracking-tighter">
                                    Indice de Match
                                </div>
                            </div>
                        </div>

                        {/* Genres */}
                        <div className="flex flex-wrap gap-2 mb-4">
                            {candidate.genres?.slice(0, 3).map((genre) => (
                                <span
                                    key={genre}
                                    className="px-2 py-0.5 bg-base-100 text-zinc-400 text-[9px] font-black uppercase tracking-widest rounded border border-base-300"
                                >
                                    {genre}
                                </span>
                            ))}
                        </div>

                        {/* Synopsis */}
                        <p className="text-zinc-400 text-sm leading-relaxed line-clamp-3 md:line-clamp-4 font-medium italic">
                            « {candidate.overview || "Aucun synopsis disponible pour ce titre."} »
                        </p>
                    </div>

                    <div className="mt-6 flex items-center justify-between">
                        <div className="text-[10px] text-zinc-500 font-black uppercase tracking-widest">
                            Généré par Apollo AI
                        </div>
                        <button
                            onClick={handleRefresh}
                            disabled={isLoading}
                            className={`px-4 py-2 bg-white text-black font-black uppercase text-[10px] tracking-widest rounded-lg hover:bg-accent hover:text-accent-content transition-colors shadow-lg shadow-white/5 active:scale-95 ${isLoading ? 'animate-pulse' : ''}`}
                        >
                            Autre idée
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
