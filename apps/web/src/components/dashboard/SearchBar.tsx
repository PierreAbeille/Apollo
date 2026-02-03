'use client';

import { useState, useEffect, useRef } from 'react';
import { searchMoviesAction } from '@/app/actions';
import { Movie } from '@/types/database';
import { useDebounce } from '@/hooks/use-debounce';
import Link from 'next/link';

export function SearchBar() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<Movie[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isOpen, setIsOpen] = useState(false);
    const wrapperRef = useRef<HTMLDivElement>(null);

    const debouncedQuery = useDebounce(query, 300);

    useEffect(() => {
        async function performSearch() {
            if (debouncedQuery.length < 2) {
                setResults([]);
                return;
            }

            setIsLoading(true);
            try {
                const data = await searchMoviesAction(debouncedQuery);
                setResults(data);
                setIsOpen(true);
            } catch (error) {
                console.error('Search failed', error);
            } finally {
                setIsLoading(false);
            }
        }

        performSearch();
    }, [debouncedQuery]);

    // Close when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    return (
        <div ref={wrapperRef} className="relative w-full max-w-md">
            <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    {isLoading ? (
                        <svg className="animate-spin h-5 w-5 text-accent" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                    ) : (
                        <svg className="h-5 w-5 text-zinc-400 group-focus-within:text-accent transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    )}
                </div>
                <input
                    type="text"
                    className="block w-full pl-10 pr-3 py-2 border border-zinc-700 rounded-xl leading-5 bg-zinc-800/50 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:bg-zinc-800 focus:ring-1 focus:ring-accent focus:border-accent sm:text-sm transition-all duration-200"
                    placeholder="Rechercher un film (Titre VF, VO ou ID)..."
                    value={query}
                    onChange={(e) => {
                        setQuery(e.target.value);
                        if (e.target.value.length >= 2) setIsOpen(true);
                    }}
                    onFocus={() => {
                        if (results.length > 0) setIsOpen(true);
                    }}
                />
            </div>

            {isOpen && (results.length > 0 || (query.length >= 2 && !isLoading)) && (
                <div className="absolute z-50 mt-2 w-full bg-zinc-900/95 backdrop-blur-xl border border-zinc-700/50 rounded-xl shadow-2xl max-h-96 overflow-y-auto overflow-x-hidden ring-1 ring-black ring-opacity-5 focus:outline-none custom-scrollbar transform transition-all animate-in fade-in slide-in-from-top-2">
                    {results.length > 0 ? (
                        <ul className="py-2">
                            {results.map((movie) => (
                                <li key={movie.tmdb_id}>
                                    <Link
                                        href={`/movie/${movie.tmdb_id}`}
                                        className="group flex items-center px-4 py-3 hover:bg-zinc-800/80 transition-all duration-150 gap-4"
                                        onClick={() => setIsOpen(false)}
                                    >
                                        <div className="flex-shrink-0 relative overflow-hidden rounded-md shadow-lg group-hover:shadow-accent/20 transition-all">
                                            {movie.poster_path ? (
                                                <img
                                                    src={`https://image.tmdb.org/t/p/w92${movie.poster_path}`}
                                                    alt={movie.title}
                                                    className="h-16 w-12 object-cover transition-transform duration-300 group-hover:scale-110"
                                                />
                                            ) : (
                                                <div className="h-16 w-12 bg-zinc-800 flex items-center justify-center text-xs text-zinc-600">
                                                    N/A
                                                </div>
                                            )}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-zinc-100 truncate group-hover:text-accent transition-colors">
                                                {movie.title}
                                            </p>
                                            <p className="text-xs text-zinc-500 flex items-center gap-2">
                                                <span>{movie.release_year || 'Inconnu'}</span>
                                                <span className="w-1 h-1 rounded-full bg-zinc-700"></span>
                                                <span className="font-mono text-[10px] opacity-70">ID: {movie.tmdb_id}</span>
                                            </p>
                                        </div>
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        !isLoading && query.length >= 2 && (
                            <div className="px-4 py-8 text-center text-sm text-zinc-500">
                                Aucun film trouvé dans la bibliothèque.
                            </div>
                        )
                    )}
                </div>
            )}
        </div>
    );
}
