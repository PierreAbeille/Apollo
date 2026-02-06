import { getMovieDetails, getMovieCredits, getImageUrl } from '@/lib/tmdb';
import { getMovieService } from '@/services/movie-service';
import { MoodAnalyzerCard } from '@/components/recommendations/MoodAnalyzerCard';
import Link from 'next/link';
import { notFound } from 'next/navigation';

export default async function MoviePage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    const movieId = parseInt(id);

    if (isNaN(movieId)) {
        notFound();
    }

    try {
        const service = await getMovieService();
        const [movie, credits, aiInsight, interaction, emotionData] = await Promise.all([
            getMovieDetails(movieId),
            getMovieCredits(movieId),
            service.getAIInsight(movieId),
            service.getInteraction(movieId),
            service.getPlutchikEmotionsForMovie(movieId)
        ]);

        const director = credits.crew.find(c => c.job === 'Director');
        const mainCast = credits.cast.slice(0, 10);
        const releaseYear = movie.release_date ? movie.release_date.split('-')[0] : 'S.A';

        const isNiche = !!movie.is_niche;
        const accentColor = isNiche ? 'text-success' : 'text-accent';
        const accentBg = isNiche ? 'bg-success/20' : 'bg-accent/20';
        const accentBorder = isNiche ? 'border-success/20' : 'border-accent/20';
        const accentFill = isNiche ? 'bg-success' : 'bg-accent';

        return (
            <main className="min-h-screen bg-base-100 text-zinc-100 pb-20">
                {/* Hero Section with Backdrop */}
                <div className="relative h-[60vh] w-full overflow-hidden">
                    {movie.backdrop_path ? (
                        <img
                            src={getImageUrl(movie.backdrop_path, 'original') || ''}
                            alt={movie.title}
                            className="w-full h-full object-cover opacity-30 scale-105 blur-sm"
                        />
                    ) : (
                        <div className="w-full h-full bg-base-200" />
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-base-100 via-base-100/20 to-transparent" />

                    <div className="absolute bottom-0 left-0 w-full p-8 md:p-16">
                        <div className="container mx-auto flex flex-col md:flex-row gap-8 items-end">
                            {/* Poster */}
                            <div className="w-48 md:w-64 flex-shrink-0 shadow-2xl rounded-xl overflow-hidden border-2 border-base-300 transform -rotate-1">
                                {movie.poster_path ? (
                                    <img src={getImageUrl(movie.poster_path, 'w500') || ''} alt={movie.title} className="w-full h-auto" />
                                ) : (
                                    <div className="aspect-[2/3] bg-base-300 flex items-center justify-center text-zinc-600 font-bold uppercase">Pas d'affiche</div>
                                )}
                            </div>

                            {/* Title & Key Info */}
                            <div className="flex-1 space-y-4">
                                <Link href="/" className="inline-flex items-center text-xs font-black uppercase tracking-widest text-zinc-500 hover:text-accent transition-colors mb-4">
                                    ← Retour au dashboard
                                </Link>
                                <div className="flex items-center gap-3 mb-2">
                                    {isNiche && (
                                        <span className="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 bg-success text-success-content rounded shadow-lg shadow-success/20">
                                            Pépite Niche
                                        </span>
                                    )}
                                    {movie.genres?.map(g => (
                                        <span key={g.id} className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 ${accentBg} ${accentColor} rounded-full border ${accentBorder}`}>
                                            {g.name}
                                        </span>
                                    ))}
                                </div>
                                <h1 className="text-4xl md:text-6xl font-black text-white tracking-tighter uppercase leading-none">
                                    {movie.title}
                                </h1>
                                <div className="flex flex-wrap items-center gap-6 text-sm font-bold text-zinc-400 uppercase tracking-widest">
                                    <span>{releaseYear}</span>
                                    {movie.runtime && <span>{Math.floor(movie.runtime / 60)}h {movie.runtime % 60}min</span>}
                                    <div className="flex items-center gap-2">
                                        <span className={accentColor}>★</span>
                                        <span>{movie.vote_average.toFixed(1)}/10</span>
                                    </div>
                                    {director && (
                                        <div className="flex items-center gap-2">
                                            <span className="text-zinc-600">•</span>
                                            <span>De <span className="text-zinc-100">{director.name}</span></span>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Content Section */}
                <div className="container mx-auto px-8 md:px-16 mt-12 grid grid-cols-1 md:grid-cols-3 gap-16">
                    <div className="md:col-span-2 space-y-12">
                        {/* Synopsis */}
                        <section className="space-y-4">
                            <h2 className="text-xl font-black text-white uppercase tracking-tight flex items-center gap-3">
                                Synopsis
                                <div className="h-px bg-base-300 flex-1" />
                            </h2>
                            <p className="text-lg leading-relaxed text-zinc-400 font-medium">
                                {movie.overview || "Aucun synopsis disponible pour ce film."}
                            </p>
                            {movie.tagline && (
                                <p className={`${accentColor} italic font-medium text-lg`}>
                                    "{movie.tagline}"
                                </p>
                            )}
                        </section>

                        {/* Cast */}
                        <section className="space-y-6">
                            <h2 className="text-xl font-black text-white uppercase tracking-tight flex items-center gap-3">
                                Distribution
                                <div className="h-px bg-base-300 flex-1" />
                            </h2>
                            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
                                {mainCast.map(person => (
                                    <div key={person.id} className="group cursor-default">
                                        <div className="aspect-[3/4] rounded-lg bg-base-200 overflow-hidden mb-2 border border-base-300">
                                            {person.profile_path ? (
                                                <img
                                                    src={getImageUrl(person.profile_path, 'w185') || ''}
                                                    alt={person.name}
                                                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                                                />
                                            ) : (
                                                <div className="w-full h-full flex items-center justify-center text-zinc-700 font-bold uppercase text-[10px]">image</div>
                                            )}
                                        </div>
                                        <p className="text-xs font-black text-white truncate">{person.name}</p>
                                        <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-tighter truncate">{person.character}</p>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>

                    {/* Sidebar / Stats */}
                    <div className="space-y-8">
                        {/* User Status Section */}
                        {interaction && (
                            <div className="bg-base-200 border border-base-300 rounded-2xl p-6 space-y-4 relative overflow-hidden group">
                                <div className={`absolute -top-12 -right-12 w-32 h-32 ${isNiche ? 'bg-success/5' : 'bg-primary/5'} blur-3xl rounded-full`} />
                                <h3 className="text-sm font-black text-white uppercase tracking-widest relative z-10">Ton Statut</h3>

                                <div className="grid grid-cols-2 gap-4 relative z-10">
                                    <div className="bg-base-100/50 p-3 rounded-xl border border-base-300/30">
                                        <p className="text-[9px] font-black text-zinc-500 uppercase tracking-tighter mb-1">Ma Note</p>
                                        <p className="text-xl font-black text-white">{interaction.rating ? `${interaction.rating}/10` : "—"}</p>
                                    </div>
                                    <div className="bg-base-100/50 p-3 rounded-xl border border-base-300/30 flex flex-col justify-center">
                                        <p className="text-[9px] font-black text-zinc-500 uppercase tracking-tighter mb-1">Actions</p>
                                        <div className="flex gap-2">
                                            {interaction.is_wishlisted && <span className={`w-2 h-2 ${accentFill} rounded-full animate-pulse`} title="Dans la wishlist" />}
                                            {interaction.is_recommended && <span className="w-2 h-2 bg-info rounded-full" title="Recommandé" />}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex flex-wrap gap-2 pt-2 relative z-10">
                                    {interaction.is_wishlisted && <span className={`text-[9px] font-black uppercase tracking-widest px-2 py-0.5 bg-zinc-800 ${isNiche ? 'text-success' : 'text-accent'} rounded`}>Wishlist</span>}
                                    {interaction.is_recommended && <span className="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 bg-info/10 text-info rounded border border-info/20">Recommandé</span>}
                                    {interaction.is_done && <span className="text-[9px] font-black uppercase tracking-widest px-2 py-0.5 bg-success/10 text-success rounded border border-success/20">Vu</span>}
                                </div>
                            </div>
                        )}
                        <div className="bg-base-200 border border-base-300 rounded-2xl p-6 space-y-6 relative overflow-hidden group">
                            <div className={`absolute -top-12 -right-12 w-32 h-32 ${isNiche ? 'bg-success/5' : 'bg-accent/5'} blur-3xl rounded-full`} />

                            <h3 className="text-sm font-black text-white uppercase tracking-widest relative z-10">Détails techniques</h3>

                            <div className="space-y-4 relative z-10">
                                <div>
                                    <p className="text-[10px] font-black text-zinc-500 uppercase tracking-tighter">Budget</p>
                                    <p className="text-sm font-bold text-zinc-200">{movie.budget > 0 ? `$${movie.budget.toLocaleString()}` : "Inconnu"}</p>
                                </div>
                                <div>
                                    <p className="text-[10px] font-black text-zinc-500 uppercase tracking-tighter">Recettes</p>
                                    <p className="text-sm font-bold text-zinc-200">{movie.revenue > 0 ? `$${movie.revenue.toLocaleString()}` : "Inconnu"}</p>
                                </div>
                                <div>
                                    <p className="text-[10px] font-black text-zinc-500 uppercase tracking-tighter">Titre original</p>
                                    <p className="text-sm font-bold text-zinc-200">{movie.original_title}</p>
                                </div>
                                {movie.homepage && (
                                    <a
                                        href={movie.homepage}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="block w-full text-center py-3 bg-base-300 hover:bg-zinc-700 border border-base-300 rounded-xl text-xs font-black uppercase tracking-widest transition-colors mt-6"
                                    >
                                        Site Officiel
                                    </a>
                                )}
                            </div>
                        </div>

                        {/* Mood Analyzer Card */}
                        {emotionData && (
                            <MoodAnalyzerCard
                                primaryEmotion={emotionData.primaryEmotion}
                                primaryScore={emotionData.primaryScore}
                                secondaryEmotion={emotionData.secondaryEmotion}
                                secondaryScore={emotionData.secondaryScore}
                                isDyad={emotionData.isDyad}
                                dyadName={emotionData.dyadName}
                                isNiche={isNiche}
                            />
                        )}

                        {/* AI Insight Section */}
                        {aiInsight && (
                            <div className={`bg-base-200 border ${isNiche ? 'border-success/30' : 'border-accent/30'} rounded-2xl p-6 space-y-4 relative overflow-hidden group shadow-lg ${isNiche ? 'shadow-success/5' : 'shadow-accent/5'}`}>
                                <div className={`absolute -top-12 -left-12 w-32 h-32 ${isNiche ? 'bg-success/10' : 'bg-accent/10'} blur-3xl rounded-full`} />

                                <div className="flex items-center justify-between relative z-10">
                                    <h3 className="text-sm font-black text-white uppercase tracking-widest">Analyse Apollo AI</h3>
                                    <div className={`px-2 py-0.5 ${accentFill} ${isNiche ? 'text-success-content' : 'text-accent-content'} text-[8px] font-black uppercase rounded`}>Batch v1</div>
                                </div>

                                <div className="pt-2 relative z-10">
                                    <div className="flex items-end gap-1">
                                        <span className={`text-5xl font-black ${accentColor} tracking-tighter leading-none`}>
                                            {aiInsight.taste_score_formatted}
                                        </span>
                                        <span className="text-xs font-black text-zinc-500 uppercase tracking-tighter mb-1">Match</span>
                                    </div>
                                </div>

                                <p className="text-xs text-zinc-400 font-medium leading-relaxed relative z-10">
                                    Ce score indique la probabilité que ce film corresponde à tes goûts actuels, basée sur ton historique de visionnage et tes notes passées.
                                </p>

                                <div className="pt-2 space-y-2 relative z-10">
                                    <div className="flex items-center justify-between text-[10px] uppercase font-black tracking-widest text-zinc-500">
                                        <span>Confiance IA</span>
                                        <span className={accentColor}>Élevée</span>
                                    </div>
                                    <div className="h-1 bg-base-300 rounded-full overflow-hidden">
                                        <div className={`h-full ${accentFill} w-[85%]`} />
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </main>
        );
    } catch (error) {
        console.error(error);
        notFound();
    }
}
