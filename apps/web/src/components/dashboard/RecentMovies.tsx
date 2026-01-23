import { Movie } from '@/types/database';
import Link from 'next/link';

export function RecentMovies({ movies }: { movies: Movie[] }) {
    return (
        <div className="bg-base-200 border border-base-300 rounded-xl p-5 h-full shadow-sm relative overflow-hidden group/main">
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-info/5 blur-[100px] rounded-full pointer-events-none group-hover/main:bg-info/10 transition-colors duration-700" />

            <div className="relative z-10">
                <div className="flex items-center justify-between mb-5">
                    <h2 className="text-lg font-black text-white tracking-tight uppercase">
                        Derniers Imports
                    </h2>
                </div>

                <div className="grid grid-cols-1 gap-2">
                    {movies.length > 0 ? (
                        movies.map((movie) => (
                            <Link
                                key={movie.tmdb_id}
                                href={`/movie/${movie.tmdb_id}`}
                                className="group flex items-center gap-3 p-2 rounded-lg bg-base-100 border border-transparent hover:border-base-300 transition-all cursor-pointer"
                            >
                                <div className="flex-shrink-0 w-8 h-12 bg-base-300 rounded overflow-hidden border border-base-300">
                                    {movie.poster_path ? (
                                        <img
                                            src={`https://image.tmdb.org/t/p/w92${movie.poster_path}`}
                                            alt={movie.title}
                                            className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-300"
                                        />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-[7px] text-zinc-600 font-black uppercase p-1 text-center">
                                            ?
                                        </div>
                                    )}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h3 className="text-sm font-bold text-zinc-200 truncate group-hover:text-info transition-colors">
                                        {movie.title}
                                    </h3>
                                    <p className="text-[10px] text-zinc-500 font-black uppercase tracking-tighter">
                                        {movie.release_year || 'S.A'}
                                    </p>
                                </div>
                            </Link>
                        ))
                    ) : (
                        <p className="text-zinc-600 font-bold uppercase tracking-widest text-[10px] py-4 text-center">Aucun import</p>
                    )}
                </div>
            </div>
        </div>
    );
}
