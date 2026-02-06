'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { MoviePoster } from '@/components/emotion-training/MoviePoster';
import { MovieInfoHeader } from '@/components/emotion-training/MovieInfoHeader';
import { MovieReview } from '@/components/emotion-training/MovieReview';
import { EmotionButtonGrid } from '@/components/emotion-training/EmotionButtonGrid';
import { TrainingProgress } from '@/components/emotion-training/TrainingProgress';
import type { MovieToLabel, PrimaryEmotionDB, EmotionTrainingProgress } from '@/types/database';
import { PRIMARY_ORDER } from '@/lib/mood-scorer';

function EmotionTrainingContent() {
    const router = useRouter();
    const searchParams = useSearchParams();

    // State
    const [movies, setMovies] = useState<MovieToLabel[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [progress, setProgress] = useState<EmotionTrainingProgress>({ total: 0, labeled: 0, remaining: 0 });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [lastLabelToast, setLastLabelToast] = useState<{ msg: string, visible: boolean } | null>(null);

    // Seed helpers
    const getSeed = () => searchParams.get('seed') || Math.floor(Math.random() * 1000000).toString();

    // Fetch data
    const fetchMovies = useCallback(async () => {
        setLoading(true);
        try {
            const seed = getSeed();
            if (!searchParams.get('seed')) {
                router.replace(`/emotion-training?seed=${seed}`);
            }

            const [moviesRes, progressRes] = await Promise.all([
                fetch(`/api/emotion-training/movies?seed=${seed}&unlabeled=true`),
                fetch('/api/emotion-training/progress')
            ]);

            const moviesData = await moviesRes.json();
            const progressData = await progressRes.json();

            setMovies(moviesData.movies || []);
            setProgress(progressData);
        } catch (error) {
            console.error('Failed to load training data', error);
        } finally {
            setLoading(false);
        }
    }, [searchParams, router]);

    useEffect(() => {
        fetchMovies();
    }, [fetchMovies]);

    // Actions
    const handleLabel = async (emotion: PrimaryEmotionDB) => {
        if (loading || saving || !movies[currentIndex]) return;

        const movie = movies[currentIndex];
        setSaving(true);

        try {
            // Optimistic update
            const nextIndex = currentIndex + 1;

            // API Call
            await fetch('/api/emotion-training/label', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tmdb_id: movie.tmdb_id,
                    emotion,
                    label_kind: 'transmitted'
                })
            });

            // Update local state
            setProgress(prev => ({
                total: prev.total,
                labeled: prev.labeled + 1,
                remaining: prev.remaining - 1
            }));

            // Show Toast
            showToast(`Label enregistré : ${emotion}`);

            // Move next
            if (nextIndex < movies.length) {
                setCurrentIndex(nextIndex);
            } else {
                // End of list, maybe fetch more or show congrats
                alert('Session terminée ! Rechargement...');
                window.location.reload();
            }

        } catch (error) {
            console.error('Failed to save label', error);
            showToast('Erreur lors de la sauvegarde');
        } finally {
            setSaving(false);
        }
    };

    const handleUndo = async () => {
        if (loading || saving) return;

        setSaving(true);
        try {
            const res = await fetch('/api/emotion-training/undo', { method: 'POST' });
            if (res.ok) {
                const data = await res.json();

                // If current movie was just skipped/passed or not, simply go back if possible
                // Actually easier: just reload progress and decrement current index if > 0
                // But specifically we want to re-show the undone movie.

                // Find index of the undone movie if it's in our list
                const undoneIndex = movies.findIndex(m => m.tmdb_id === data.tmdb_id);

                setProgress(prev => ({
                    total: prev.total,
                    labeled: Math.max(0, prev.labeled - 1),
                    remaining: prev.remaining + 1
                }));

                showToast('Dernier label annulé');

                if (undoneIndex !== -1) {
                    setCurrentIndex(undoneIndex);
                } else if (currentIndex > 0) {
                    // Fallback to previous in list if exact ID match fails
                    setCurrentIndex(currentIndex - 1);
                }

            } else {
                showToast('Rien à annuler');
            }
        } catch (error) {
            console.error('Failed to undo', error);
        } finally {
            setSaving(false);
        }
    };

    const handleSkip = () => {
        if (currentIndex < movies.length - 1) {
            setCurrentIndex(currentIndex + 1);
        }
    };

    const showToast = (msg: string) => {
        setLastLabelToast({ msg, visible: true });
        setTimeout(() => setLastLabelToast(prev => prev ? { ...prev, visible: false } : null), 2000);
    };

    // Keyboard Shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (loading || saving) return;

            // Emotions 1-8
            const key = parseInt(e.key);
            if (key >= 1 && key <= 8) {
                const emotion = PRIMARY_ORDER[key - 1];
                if (emotion) handleLabel(emotion as PrimaryEmotionDB);
                return;
            }

            // Undo (Ctrl/Cmd + Z)
            if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
                e.preventDefault();
                handleUndo();
                return;
            }

            // Navigation
            if (e.key === 'ArrowRight') handleSkip();
            if (e.key === 'ArrowLeft' && currentIndex > 0) setCurrentIndex(currentIndex - 1);
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [currentIndex, loading, saving, movies]);

    const currentMovie = movies[currentIndex];

    if (loading) return (
        <div className="min-h-screen flex items-center justify-center bg-base-100 text-zinc-500">
            Chargement de la session...
        </div>
    );

    if (!currentMovie) return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-base-100 space-y-4">
            <h1 className="text-2xl font-black text-white">Aucun film à labelliser</h1>
            <p className="text-zinc-500">Tu as tout vu ! (ou tout labellisé)</p>
            <button onClick={() => window.location.reload()} className="btn btn-primary">
                Recharger
            </button>
        </div>
    );

    return (
        <main className="min-h-screen bg-base-100 text-zinc-100 flex items-center justify-center p-4">

            {/* Main Card */}
            <div className="w-full max-w-6xl h-[90vh] grid grid-cols-12 gap-0 bg-base-200 border border-zinc-800 rounded-3xl overflow-hidden shadow-2xl relative">

                {/* Left Column: Poster (4 cols) */}
                <div className="col-span-4 h-full relative border-r border-zinc-800/50">
                    <MoviePoster
                        posterPath={currentMovie.poster_path}
                        title={currentMovie.title}
                    />

                    {/* Navigation overlay */}
                    <div className="absolute inset-x-0 bottom-0 p-6 bg-gradient-to-t from-black/80 to-transparent flex justify-between items-end opacity-0 hover:opacity-100 transition-opacity">
                        <button
                            onClick={handleUndo}
                            className="text-xs font-bold text-zinc-400 hover:text-white flex items-center gap-2"
                        >
                            <span>↩</span> Annuler (Cmd+Z)
                        </button>
                    </div>
                </div>

                {/* Right Column: Interaction (8 cols) */}
                <div className="col-span-8 h-full flex flex-col">

                    {/* Header Section */}
                    <div className="p-8 pb-4 border-b border-zinc-800/50">
                        <div className="flex justify-between items-start mb-6">
                            <div className="flex-1">
                                <MovieInfoHeader
                                    title={currentMovie.title}
                                    releaseYear={currentMovie.release_year}
                                    rating={currentMovie.rating}
                                    overview={currentMovie.overview}
                                />
                            </div>
                            <div className="w-48 pl-8 border-l border-zinc-800/30">
                                <TrainingProgress
                                    progress={progress}
                                    currentIndex={currentIndex}
                                />
                            </div>
                        </div>

                        <MovieReview reviewText={currentMovie.review_text} />
                    </div>

                    {/* Action Section (Fill remaining height) */}
                    <div className="flex-1 p-8 bg-base-200/50 flex flex-col justify-center">
                        <div className="max-w-3xl mx-auto w-full">
                            <EmotionButtonGrid
                                onSelect={handleLabel}
                                disabled={saving}
                            />
                        </div>
                    </div>

                    {/* Footer / Controls */}
                    <div className="p-4 border-t border-zinc-800/50 bg-base-300/30 flex justify-between items-center text-xs text-zinc-500 font-mono">
                        <div className="flex gap-4">
                            <span>← Précédent</span>
                            <span>→ Suivant (Skip)</span>
                        </div>
                        <div>
                            Session ID: {getSeed().slice(0, 8)}
                        </div>
                    </div>
                </div>

                {/* Toast Overlay */}
                <div className={`
                    absolute top-6 right-6 px-4 py-2 bg-success text-success-content 
                    rounded-lg font-bold shadow-lg transform transition-all duration-300
                    ${lastLabelToast && lastLabelToast.visible ? 'translate-y-0 opacity-100' : '-translate-y-4 opacity-0'}
                `}>
                    {lastLabelToast?.msg}
                </div>

                {/* Saving Indicator */}
                {saving && (
                    <div className="absolute inset-0 bg-black/20 backdrop-blur-[1px] flex items-center justify-center z-50">
                        <span className="loading loading-spinner text-primary text-2xl"></span>
                    </div>
                )}
            </div>
        </main>
    );
}

export default function EmotionTrainingPage() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-base-100 flex items-center justify-center">Chargement...</div>}>
            <EmotionTrainingContent />
        </Suspense>
    );
}
