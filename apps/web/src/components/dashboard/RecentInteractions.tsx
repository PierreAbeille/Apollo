import { Interaction } from '@/types/database';

export function RecentInteractions({ interactions }: { interactions: Interaction[] }) {
    return (
        <div className="bg-base-200 border border-base-300 rounded-xl p-5 h-full shadow-sm relative overflow-hidden group">
            <div className="absolute -bottom-24 -right-24 w-64 h-64 bg-warning/5 blur-[100px] rounded-full pointer-events-none group-hover:bg-warning/10 transition-colors duration-700" />

            <div className="relative z-10">
                <div className="flex items-center justify-between mb-5">
                    <h2 className="text-lg font-black text-white tracking-tight uppercase">
                        Activité
                    </h2>
                </div>

                <div className="space-y-2">
                    {interactions.length > 0 ? (
                        interactions.map((it) => (
                            <div
                                key={it.id}
                                className="flex items-center justify-between p-3 rounded-lg bg-base-100 border border-base-300/30 hover:border-base-300 transition-all"
                            >
                                <div className="flex items-center gap-3 min-w-0">
                                    <div className="w-1.5 h-6 bg-base-300 rounded-full overflow-hidden">
                                        <div className={`w-full h-full ${it.rating && it.rating >= 8 ? 'bg-success' : 'bg-warning'}`} />
                                    </div>
                                    <div className="min-w-0">
                                        <h3 className="text-sm font-bold text-zinc-100 truncate">
                                            {(it as any).title || `Film #${it.tmdb_id}`}
                                        </h3>
                                        <div className="flex items-center gap-2 mt-0.5">
                                            {it.rating && (
                                                <span className="text-[10px] font-black text-zinc-500 uppercase tracking-tighter">
                                                    Note : {it.rating}/10
                                                </span>
                                            )}
                                            {it.is_wishlisted && <span className="text-[9px] font-black text-accent uppercase tracking-tighter">Wishlist</span>}
                                            {it.is_recommended && <span className="text-[9px] font-black text-info uppercase tracking-tighter">Recommandé</span>}
                                        </div>
                                    </div>
                                </div>
                                <div className="text-[9px] font-black text-zinc-600 uppercase tracking-tighter text-right ml-4 shrink-0">
                                    {new Date(it.created_at).toLocaleDateString('fr-FR')}
                                </div>
                            </div>
                        ))
                    ) : (
                        <p className="text-zinc-600 font-bold uppercase tracking-widest text-[10px] py-4 text-center">Aucune activité</p>
                    )}
                </div>
            </div>
        </div>
    );
}
