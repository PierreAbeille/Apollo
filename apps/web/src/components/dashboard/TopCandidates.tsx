import { TasteCandidate } from '@/types/database';
import Link from 'next/link';

export function TopCandidates({ candidates }: { candidates: TasteCandidate[] }) {
    return (
        <div className="bg-base-200 border border-base-300 rounded-xl p-5 h-full shadow-sm relative overflow-hidden group/main">
            <div className="absolute -top-24 -left-24 w-64 h-64 bg-accent/5 blur-[100px] rounded-full pointer-events-none group-hover/main:bg-accent/10 transition-colors duration-700" />

            <div className="relative z-10">
                <div className="flex items-center justify-between mb-5">
                    <h2 className="text-lg font-black text-white tracking-tight uppercase">
                        Recommandations IA
                    </h2>
                    <Link href="/recommandations" className="text-zinc-500 text-[9px] font-black uppercase tracking-widest hover:text-accent transition-colors underline decoration-zinc-500/30 underline-offset-4 cursor-pointer">
                        Voir tout →
                    </Link>
                </div>

                <div className="space-y-2">
                    {candidates.length > 0 ? (
                        candidates.map((candidate, idx) => (
                            <Link
                                key={candidate.id}
                                href={`/movie/${candidate.tmdb_id}`}
                                className="group flex items-center gap-3 p-2 rounded-lg bg-base-100 border border-transparent hover:border-base-300 transition-all cursor-pointer"
                            >
                                <div className="flex-shrink-0 w-10 h-14 bg-base-300 rounded overflow-hidden border border-base-300 relative">
                                    {candidate.poster_path ? (
                                        <img
                                            src={`https://image.tmdb.org/t/p/w92${candidate.poster_path}`}
                                            alt={candidate.title}
                                            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                                        />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-[7px] text-zinc-600 font-bold uppercase p-1 text-center">
                                            ?
                                        </div>
                                    )}
                                    <div className="absolute top-0 left-0 bg-black/60 text-[8px] font-bold px-1 py-0.5 rounded-br">
                                        #{idx + 1}
                                    </div>
                                </div>

                                <div className="flex-1 min-w-0">
                                    <h3 className="text-sm font-bold text-zinc-100 truncate group-hover:text-accent transition-colors">
                                        {candidate.title}
                                    </h3>
                                    <p className="text-[10px] text-zinc-500 font-black uppercase tracking-tighter">
                                        {candidate.release_year || 'S.A'}
                                    </p>
                                </div>

                                <div className="flex flex-col items-end">
                                    <div className="text-lg font-black text-accent tracking-tighter group-hover:scale-105 transition-transform">
                                        {(candidate.taste_score * 100).toFixed(0)}%
                                    </div>
                                    <div className="text-[8px] text-zinc-600 font-black uppercase tracking-tighter">
                                        Match
                                    </div>
                                </div>
                            </Link>
                        ))
                    ) : (
                        <div className="py-8 text-center">
                            <p className="text-zinc-600 font-bold uppercase tracking-widest text-[10px]">Aucun candidat</p>
                        </div>
                    )}
                </div>
            </div>
        </div >
    );
}
