'use client';

import { useState } from 'react';

interface MovieReviewProps {
    reviewText: string | null;
}

export function MovieReview({ reviewText }: MovieReviewProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const maxLength = 150;
    const shouldTruncate = reviewText && reviewText.length > maxLength;

    return (
        <div className="space-y-2">
            <h3 className="text-xs font-black text-zinc-400 uppercase tracking-widest">Ma Review</h3>

            {reviewText ? (
                <div className="bg-base-300/50 border border-zinc-700/30 rounded-xl p-4">
                    <p className="text-sm text-zinc-300 leading-relaxed italic">
                        "{shouldTruncate && !isExpanded
                            ? `${reviewText.slice(0, maxLength)}...`
                            : reviewText
                        }"
                    </p>
                    {shouldTruncate && (
                        <button
                            onClick={() => setIsExpanded(!isExpanded)}
                            className="text-xs font-bold text-accent uppercase tracking-widest hover:underline mt-2"
                        >
                            {isExpanded ? 'Réduire' : 'Lire plus'}
                        </button>
                    )}
                </div>
            ) : (
                <div className="bg-base-300/30 border border-zinc-700/20 rounded-xl p-4 text-center">
                    <span className="text-sm text-zinc-500 italic">Aucune review</span>
                </div>
            )}
        </div>
    );
}
