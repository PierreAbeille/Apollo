'use client';

import { getImageUrl } from '@/lib/tmdb';

interface MoviePosterProps {
    posterPath: string | null;
    title: string;
}

export function MoviePoster({ posterPath, title }: MoviePosterProps) {
    return (
        <div className="w-full h-full flex items-center justify-center bg-base-300 rounded-2xl overflow-hidden shadow-2xl">
            {posterPath ? (
                <img
                    src={getImageUrl(posterPath, 'w780') || ''}
                    alt={title}
                    className="w-full h-full object-cover"
                />
            ) : (
                <div className="flex flex-col items-center justify-center text-zinc-500 p-8">
                    <span className="text-6xl mb-4">🎬</span>
                    <span className="text-sm font-bold uppercase tracking-widest">Pas d'affiche</span>
                </div>
            )}
        </div>
    );
}
