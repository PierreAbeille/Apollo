import { getMovieService } from '@/services/movie-service';
import Link from 'next/link';
import { getImageUrl } from '@/lib/tmdb';
import { GenreMoodFilter } from '@/components/recommendations/GenreMoodFilter';
import { Suspense } from 'react';

export default async function RecommandationsPage({
    searchParams
}: {
    searchParams: Promise<{ page?: string; mood?: string }>
}) {
    const params = await searchParams;
    const currentPage = parseInt(params.page || '1');
    const moodId = params.mood;
    const pageSize = 50;

    const service = await getMovieService();
    const { data: candidates, count } = await service.getAllCandidatesPaginated(currentPage, pageSize, moodId);

    const totalPages = Math.ceil(count / pageSize);

    return (
        <main className="min-h-screen bg-base-100 text-zinc-100 p-8 md:p-16 pb-32">
            <div className="container mx-auto space-y-12">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div>
                        <Link href="/" className="inline-flex items-center text-xs font-black uppercase tracking-widest text-zinc-500 hover:text-accent transition-colors mb-6">
                            ← Dashboard
                        </Link>
                        <h1 className="text-4xl md:text-6xl font-black text-white tracking-tighter uppercase leading-none">
                            Toutes les <span className="text-accent underline decoration-accent/30 underline-offset-8 italic">recommandations</span>
                        </h1>
                        <p className="mt-4 text-zinc-500 font-bold uppercase tracking-widest text-[10px] flex items-center gap-2">
                            <span className="w-2 h-2 bg-accent rounded-full animate-pulse" />
                            {count} films analysés par Apollo AI
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                        <Suspense fallback={<div className="h-10 w-64 bg-base-200 rounded-xl animate-pulse" />}>
                            <GenreMoodFilter />
                        </Suspense>
                        <div className="px-4 py-2 bg-base-200 border border-base-300 rounded-xl shadow-inner h-[46px] flex flex-col justify-center">
                            <span className="text-[9px] font-black uppercase tracking-widest text-zinc-600 block mb-0.5 leading-none">Collection</span>
                            <span className="text-sm font-black text-white uppercase tracking-tighter">Batch v1.0</span>
                        </div>
                        <div className="px-4 py-2 bg-base-200 border border-base-300 rounded-xl shadow-inner text-right min-w-[100px] h-[46px] flex flex-col justify-center">
                            <span className="text-[9px] font-black uppercase tracking-widest text-zinc-600 block mb-0.5 leading-none">Page</span>
                            <span className="text-sm font-black text-white">{currentPage} <span className="text-zinc-600">/</span> {totalPages}</span>
                        </div>
                    </div>
                </div>

                {/* Table View */}
                <div className="bg-base-200 border border-base-300 rounded-2xl overflow-hidden shadow-2xl">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-base-300 bg-base-300/30">
                                    <th className="p-4 py-3 text-[10px] font-black uppercase tracking-widest text-zinc-500">Rang</th>
                                    <th className="p-4 py-3 text-[10px] font-black uppercase tracking-widest text-zinc-500">Film</th>
                                    <th className="p-4 py-3 text-[10px] font-black uppercase tracking-widest text-zinc-500">Année</th>
                                    <th className="p-4 py-3 text-[10px] font-black uppercase tracking-widest text-zinc-500">Statut</th>
                                    <th className="p-4 py-3 text-[10px] font-black uppercase tracking-widest text-zinc-500 text-right">Score match</th>
                                    <th className="p-4 py-3 text-[10px] font-black uppercase tracking-widest text-zinc-500 text-right pr-8">Détails</th>
                                </tr>
                            </thead>
                            <tbody>
                                {candidates.length > 0 ? (
                                    candidates.map((movie, index) => {
                                        const rank = (currentPage - 1) * pageSize + index + 1;
                                        const isNiche = !!movie.is_niche;
                                        const accentColor = isNiche ? 'text-success' : 'text-accent';

                                        return (
                                            <tr key={movie.tmdb_id} className="border-b border-base-300/50 hover:bg-base-300/20 transition-colors group">
                                                <td className="p-4 text-xs font-black text-zinc-600">
                                                    #{rank.toString().padStart(2, '0')}
                                                </td>
                                                <td className="p-4">
                                                    <div className="flex items-center gap-4">
                                                        <div className="w-8 h-12 bg-base-300 rounded overflow-hidden flex-shrink-0 border border-base-300 shadow-sm">
                                                            {movie.poster_path ? (
                                                                <img
                                                                    src={getImageUrl(movie.poster_path, 'w92') || ''}
                                                                    alt={movie.title}
                                                                    className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all"
                                                                />
                                                            ) : (
                                                                <div className="w-full h-full flex items-center justify-center text-[8px] text-zinc-700">?</div>
                                                            )}
                                                        </div>
                                                        <div>
                                                            <h3 className="text-sm font-black text-white group-hover:text-accent transition-colors truncate max-w-[200px] md:max-w-md">
                                                                {movie.title}
                                                            </h3>
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="p-4 text-xs font-bold text-zinc-500">
                                                    {movie.release_year || 'S.A'}
                                                </td>
                                                <td className="p-4">
                                                    {isNiche ? (
                                                        <span className="text-[10px] font-black uppercase px-2 py-0.5 bg-success/10 text-success rounded border border-success/20">Niche</span>
                                                    ) : (
                                                        <span className="text-[10px] font-black uppercase px-2 py-0.5 bg-accent/10 text-accent rounded border border-accent/20 text-center inline-block min-w-[60px]">Public</span>
                                                    )}
                                                </td>
                                                <td className="p-4 text-right">
                                                    <div className="inline-flex flex-col items-end">
                                                        <span className={`text-xl font-black ${accentColor} tracking-tighter leading-none`}>
                                                            {(movie.taste_score * 100).toFixed(0)}%
                                                        </span>
                                                        <div className="w-full h-1 bg-zinc-800 rounded-full mt-1 overflow-hidden">
                                                            <div className={`h-full ${isNiche ? 'bg-success' : 'bg-accent'} transition-all`} style={{ width: `${movie.taste_score * 100}%` }} />
                                                        </div>
                                                    </div>
                                                </td>
                                                <td className="p-4 text-right pr-8">
                                                    <Link
                                                        href={`/movie/${movie.tmdb_id}`}
                                                        className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-base-300 text-zinc-400 hover:bg-white hover:text-black transition-all"
                                                    >
                                                        →
                                                    </Link>
                                                </td>
                                            </tr>
                                        );
                                    })
                                ) : (
                                    <tr>
                                        <td colSpan={6} className="p-20 text-center">
                                            <div className="flex flex-col items-center gap-2">
                                                <span className="text-3xl">🏜️</span>
                                                <p className="text-sm font-black text-zinc-500 uppercase tracking-widest">Aucun film trouvé pour ce mood</p>
                                                <Link href="/recommandations" className="text-accent text-[10px] font-black uppercase underline mt-4">Voir tout</Link>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-center gap-2">
                    {currentPage > 1 && (
                        <Link
                            href={`/recommandations?page=${currentPage - 1}${moodId ? `&mood=${moodId}` : ''}`}
                            className="px-6 py-3 bg-base-200 border border-base-300 rounded-xl text-xs font-black uppercase tracking-widest hover:border-accent transition-colors"
                        >
                            Précédent
                        </Link>
                    )}
                    {currentPage < totalPages && (
                        <Link
                            href={`/recommandations?page=${currentPage + 1}${moodId ? `&mood=${moodId}` : ''}`}
                            className="px-6 py-3 bg-base-200 border border-base-300 rounded-xl text-xs font-black uppercase tracking-widest hover:border-accent transition-colors"
                        >
                            Suivant
                        </Link>
                    )}
                </div>
            </div>
        </main>
    );
}
