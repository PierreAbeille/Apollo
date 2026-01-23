import { Interaction } from '@/types/database';

export function RecentInteractions({ interactions }: { interactions: Interaction[] }) {
    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-8 h-full">
            <div className="flex items-center justify-between mb-8">
                <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
                    <span className="p-2 bg-amber-500/10 rounded-xl text-amber-400 text-sm">⭐</span>
                    Activité
                </h2>
            </div>

            <div className="space-y-3">
                {interactions.length > 0 ? (
                    interactions.map((it) => (
                        <div
                            key={it.id}
                            className="flex items-center justify-between p-4 rounded-2xl bg-zinc-800/10 border border-zinc-800/50 hover:bg-zinc-800/20 transition-all"
                        >
                            <div className="flex items-center gap-3 min-w-0">
                                <div className="w-2 h-8 bg-zinc-800 rounded-full overflow-hidden">
                                    <div className={`w-full h-full bg-gradient-to-t ${it.rating && it.rating >= 8 ? 'from-green-500 to-emerald-400' : 'from-amber-600 to-orange-400'}`} />
                                </div>
                                <div className="min-w-0">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-1">TMDB {it.tmdb_id}</p>
                                    <div className="flex items-center gap-2">
                                        {it.rating && (
                                            <span className="px-2 py-0.5 bg-zinc-800 rounded text-xs font-black text-white border border-zinc-700">
                                                {it.rating}/10
                                            </span>
                                        )}
                                        {it.is_wishlisted && <span className="text-xs">🏷️</span>}
                                        {it.is_recommended && <span className="text-xs">👍</span>}
                                    </div>
                                </div>
                            </div>
                            <div className="text-[10px] font-bold text-zinc-600 uppercase tracking-tighter">
                                {new Date(it.created_at).toLocaleDateString()}
                            </div>
                        </div>
                    ))
                ) : (
                    <p className="text-zinc-600 font-bold uppercase tracking-widest text-xs py-8 text-center text-zinc-500">Aucune interaction</p>
                )}
            </div>
        </div>
    );
}
