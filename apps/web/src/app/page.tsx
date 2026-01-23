import { getMovieService } from '@/services/movie-service';
import { StatsGrid } from '@/components/dashboard/StatsGrid';
import { RecentMovies } from '@/components/dashboard/RecentMovies';
import { RecentInteractions } from '@/components/dashboard/RecentInteractions';
import { TopCandidates } from '@/components/dashboard/TopCandidates';
import { FeaturedRecommendation } from '@/components/dashboard/FeaturedRecommendation';

export const dynamic = 'force-dynamic';

export default async function Page() {
  const movieService = await getMovieService();

  // Parallel fetching for performance
  const [stats, recentMovies, recentInteractions, topCandidates, featured] = await Promise.all([
    movieService.getStats(),
    movieService.getRecentMovies(6),
    movieService.getRecentInteractions(5),
    movieService.getTopCandidates(8),
    movieService.getRandomRecommendation(),
  ]);

  return (
    <div className="min-h-screen bg-base-100 text-base-content selection:bg-primary/30">
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <header className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="h-1 w-8 bg-zinc-800 rounded-full" />
              <span className="text-zinc-500 font-bold uppercase tracking-widest text-[10px]">Intelligence Cinématographique</span>
            </div>
            <h1 className="text-3xl font-black tracking-tight text-white uppercase">
              Apollo<span className="text-accent">.</span>
            </h1>
          </div>

          <div className="flex items-center gap-3 bg-base-200 px-4 py-2 rounded-xl border border-base-300 shadow-sm">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-success"></span>
            </span>
            <span className="text-[10px] font-black uppercase tracking-widest text-success">Système Opérationnel</span>
          </div>
        </header>

        {/* Stats Section */}
        <StatsGrid stats={stats} />

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Recommendations */}
          <div className="lg:col-span-4 self-start">
            <TopCandidates candidates={topCandidates} />
          </div>

          {/* Right Column: Activity & Library */}
          <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Featured Recommendation - Now at the Top */}
            <FeaturedRecommendation initialCandidate={featured} />

            <RecentMovies movies={recentMovies} />
            <RecentInteractions interactions={recentInteractions} />
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-20 pt-8 border-t border-base-300 text-center">
          <p className="text-[9px] font-black uppercase tracking-[0.4em] text-zinc-600">
            © 2026 Apollo — <a href="https://www.hellopedro.dev" target="_blank" className="text-zinc-500 hover:text-accent transition-colors">hellopedro.dev</a>
          </p>
        </footer>
      </main>
    </div>
  );
}
