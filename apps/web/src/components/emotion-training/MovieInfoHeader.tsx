'use client';

import { useState } from 'react';

interface MovieInfoHeaderProps {
    title: string;
    releaseYear: number | null;
    rating: number | null;
    overview: string | null;
}

export function MovieInfoHeader({ title, releaseYear, rating, overview }: MovieInfoHeaderProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const maxLength = 200;
    const shouldTruncate = overview && overview.length > maxLength;

    return (
        <div className="space-y-4">
            {/* Title + Year + Rating */}
            <div className="flex items-start justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-black text-white uppercase tracking-tight leading-tight">
                        {title}
                    </h2>
                    {releaseYear && (
                        <span className="text-sm font-bold text-zinc-500 uppercase tracking-widest">
                            {releaseYear}
                        </span>
                    )}
                </div>
                {rating !== null && (
                    <div className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 bg-accent/20 text-accent rounded-xl border border-accent/30">
                        <span className="text-lg">★</span>
                        <span className="text-xl font-black">{rating}</span>
                        <span className="text-xs text-zinc-400">/10</span>
                    </div>
                )}
            </div>

            {/* Synopsis */}
            {overview && (
                <div className="space-y-2">
                    <h3 className="text-xs font-black text-zinc-400 uppercase tracking-widest">Synopsis</h3>
                    <p className="text-sm text-zinc-300 leading-relaxed">
                        {shouldTruncate && !isExpanded
                            ? `${overview.slice(0, maxLength)}...`
                            : overview
                        }
                    </p>
                    {shouldTruncate && (
                        <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="text-xs font-bold text-accent uppercase tracking-widest hover:underline"
                        >
                            {isExpanded ? 'Réduire' : 'Lire plus'}
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}
