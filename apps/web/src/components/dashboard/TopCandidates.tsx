import { TasteCandidate } from '@/types/database';

export function TopCandidates({ candidates }: { candidates: TasteCandidate[] }) {
    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-8 h-full">
            <div className="flex items-center justify-between mb-8">
                <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
                    <span className="p-2 bg-indigo-500/10 rounded-xl text-indigo-400 text-sm">🎯</span>
                    Recommandations IA
                </h2>
                <span className="text-zinc-500 text-xs font-bold uppercase tracking-widest bg-zinc-800 px-3 py-1 rounded-full">
                    Top {candidates.length}
                </span>
            </div>

            <div className="space-y-4">
                {candidates.length > 0 ? (
                    candidates.map((candidate, idx) => (
                        <div
                            key={candidate.id}
                            className="group flex items-center gap-4 p-4 rounded-2xl bg-zinc-900 border border-transparent hover:border-zinc-800 hover:bg-zinc-800/50 transition-all cursor-default"
                        >
                            <div className="flex-shrink-0 w-12 h-16 bg-zinc-800 rounded-lg overflow-hidden border border-zinc-700 relative">
                                {candidate.poster_path ? (
                                    <img
                                        src={`https://image.tmdb.org/t/p/w92${candidate.poster_path}`}
                                        alt={candidate.title}
                                        className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                                    />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center text-[10px] text-zinc-600 font-bold uppercase p-1 text-center">
                                        No Poster
                                    </div>
                                )}
                                <div className="absolute top-0 left-0 bg-black/60 text-[10px] font-bold px-1.5 py-0.5 rounded-br">
                                    #{idx + 1}
                                </div>
                            </div>

                            <div className="flex-1 min-w-0">
                                <h3 className="text-sm font-bold text-zinc-100 truncate group-hover:text-indigo-400 transition-colors">
                                    {candidate.title}
                                </h3>
                                <p className="text-xs text-zinc-500 font-medium">
                                    {candidate.release_year || 'Année inconnue'}
                                </p>
                            </div>

                            <div className="flex flex-col items-end">
                                <div className="text-lg font-black text-indigo-400 tracking-tighter">
                                    {(candidate.taste_score * 100).toFixed(0)}%
                                </div>
                                <div className="text-[10px] text-zinc-600 font-black uppercase tracking-tighter">
                                    Match
                                </div>
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="py-12 text-center">
                        <p className="text-zinc-600 font-bold uppercase tracking-widest text-xs">Aucun candidat pour le moment</p>
                    </div>
                )}
            </div>
        </div>
    );
}
