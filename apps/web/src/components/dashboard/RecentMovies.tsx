import { Movie } from '@/types/database';

export function RecentMovies({ movies }: { movies: Movie[] }) {
    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-8 h-full">
            <div className="flex items-center justify-between mb-8">
                <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
                    <span className="p-2 bg-blue-500/10 rounded-xl text-blue-400 text-sm">📽️</span>
                    Derniers Imports
                </h2>
            </div>

            <div className="grid grid-cols-1 gap-4">
                {movies.length > 0 ? (
                    movies.map((movie) => (
                        <div
                            key={movie.tmdb_id}
                            className="group flex items-center gap-4 p-3 rounded-2xl hover:bg-zinc-800/30 transition-all border border-transparent hover:border-zinc-800"
                        >
                            <div className="flex-shrink-0 w-10 h-14 bg-zinc-800 rounded-lg overflow-hidden border border-zinc-700">
                                {movie.poster_path ? (
                                    <img
                                        src={`https://image.tmdb.org/t/p/w92${movie.poster_path}`}
                                        alt={movie.title}
                                        className="w-full h-full object-cover"
                                    />
                                ) : (
                                    <div className="w-full h-full flex items-center justify-center text-[8px] text-zinc-600 font-bold uppercase p-1 text-center">
                                        ?
                                    </div>
                                )}
                            </div>
                            <div className="flex-1 min-w-0">
                                <h3 className="text-sm font-bold text-zinc-200 truncate group-hover:text-blue-400 transition-colors">
                                    {movie.title}
                                </h3>
                                <p className="text-[10px] text-zinc-500 font-black uppercase tracking-widest mt-0.5">
                                    {movie.release_year || 'N/A'}
                                </p>
                            </div>
                        </div>
                    ))
                ) : (
                    <p className="text-zinc-600 font-bold uppercase tracking-widest text-xs py-8 text-center">Vide</p>
                )}
            </div>
        </div>
    );
}
