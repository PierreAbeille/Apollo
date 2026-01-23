import { getMovieService } from '@/services/movie-service';
import { StatsGrid } from '@/components/dashboard/StatsGrid';
import { RecentMovies } from '@/components/dashboard/RecentMovies';
import { RecentInteractions } from '@/components/dashboard/RecentInteractions';
import { TopCandidates } from '@/components/dashboard/TopCandidates';

export const dynamic = 'force-dynamic';

export default async function Page() {
  const movieService = await getMovieService();

  // Parallel fetching for performance
  const [stats, recentMovies, recentInteractions, topCandidates] = await Promise.all([
    movieService.getStats(),
    movieService.getRecentMovies(6),
    movieService.getRecentInteractions(5),
    movieService.getTopCandidates(8),
  ]);

  return (
    <div className="min-h-screen bg-black text-white selection:bg-indigo-500/30">
      {/* Background Decor */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-500/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/10 blur-[120px] rounded-full" />
      </div>

      <main className="relative z-10 max-w-7xl mx-auto px-6 py-12 lg:py-20">
        {/* Header */}
        <header className="mb-16 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <span className="h-0.5 w-12 bg-indigo-500 rounded-full" />
              <span className="text-zinc-500 font-black uppercase tracking-[0.3em] text-xs">Intelligence Cinématographique</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-black tracking-tighter text-white">
              Apollo<span className="text-indigo-500">.</span>
            </h1>
          </div>

          <div className="text-left md:text-right">
            <p className="text-zinc-500 font-bold uppercase tracking-widest text-[10px] mb-2">Statut du Système</p>
            <div className="flex items-center md:justify-end gap-2">
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-xs font-black text-emerald-500 uppercase tracking-tighter">Opérationnel</span>
            </div>
          </div>
        </header>

        {/* Stats Section */}
        <StatsGrid stats={stats} />

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Recommendations */}
          <div className="lg:col-span-4 h-full">
            <TopCandidates candidates={topCandidates} />
          </div>

          {/* Right Column: Activity & Library */}
          <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-8">
            <RecentMovies movies={recentMovies} />
            <RecentInteractions interactions={recentInteractions} />

            {/* Quick Action / Info Card */}
            <div className="md:col-span-2 bg-gradient-to-br from-indigo-600 to-blue-700 rounded-3xl p-8 flex flex-col md:flex-row items-center justify-between gap-8 shadow-2xl shadow-indigo-500/20">
              <div>
                <h3 className="text-2xl font-black text-white tracking-tight mb-2">Prêt pour plus ?</h3>
                <p className="text-indigo-100/70 font-medium max-w-md">
                  Le pipeline ML analyse tes goûts pour découvrir les pépites qui manquent à ta collection.
                </p>
              </div>
              <button disabled className="bg-white text-indigo-600 px-8 py-3 rounded-2xl font-black uppercase tracking-widest text-xs hover:scale-105 transition-transform opacity-50 cursor-not-allowed">
                Bientôt Disponible
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-32 pt-12 border-t border-zinc-900 flex flex-col md:flex-row justify-between items-center gap-6 text-zinc-600">
          <p className="text-sm font-bold tracking-tight">© 2026 Apollo Intelligence. Tous droits réservés.</p>
          <div className="flex gap-8 text-[10px] font-black uppercase tracking-[0.2em]">
            <span className="hover:text-zinc-400 cursor-pointer transition-colors">Système</span>
            <span className="hover:text-zinc-400 cursor-pointer transition-colors">Algorithme</span>
            <span className="hover:text-zinc-400 cursor-pointer transition-colors">Confidentialité</span>
          </div>
        </footer>
      </main>
    </div>
  );
}
