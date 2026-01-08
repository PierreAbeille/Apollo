import { createClient } from '@/utils/supabase/server'
import { cookies } from 'next/headers'

interface Movie {
  tmdb_id: number;
  title: string;
  release_year: number | null;
  poster_path: string | null;
  updated_at: string;
}

interface Interaction {
  id: number;
  tmdb_id: number;
  rating: number | null;
  is_done: boolean;
  is_wishlisted: boolean;
  is_recommended: boolean;
  source: string;
  created_at: string;
}

interface TasteCandidate {
  id: number;
  tmdb_id: number;
  taste_score: number;
  model_version: string;
  generated_at: string;
}

async function getStats(supabase: ReturnType<typeof createClient>) {
  const [moviesRes, interactionsRes, candidatesRes, historyRes] = await Promise.all([
    supabase.from('movies').select('*', { count: 'exact', head: true }),
    supabase.from('interactions').select('*', { count: 'exact', head: true }),
    supabase.from('taste_candidates').select('*', { count: 'exact', head: true }),
    supabase.from('recommendation_history').select('*', { count: 'exact', head: true }),
  ]);

  return {
    movies: moviesRes.count ?? 0,
    interactions: interactionsRes.count ?? 0,
    candidates: candidatesRes.count ?? 0,
    history: historyRes.count ?? 0,
  };
}

export default async function Page() {
  const cookieStore = await cookies()
  const supabase = createClient(cookieStore)

  const stats = await getStats(supabase);

  const { data: recentMovies } = await supabase
    .from('movies')
    .select('*')
    .order('updated_at', { ascending: false })
    .limit(5);

  const { data: recentInteractions } = await supabase
    .from('interactions')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(5);

  const { data: topCandidates } = await supabase
    .from('taste_candidates')
    .select('*')
    .order('taste_score', { ascending: false })
    .limit(5);

  return (
    <div className="min-h-screen bg-zinc-900 text-zinc-100 p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold">🎬 Apollo — Movie Reco Dashboard</h1>
        <p className="text-zinc-400 mt-2">PoC Dashboard for movie recommendations</p>
      </header>

      {/* Stats Grid */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Movies" value={stats.movies} />
        <StatCard label="Interactions" value={stats.interactions} />
        <StatCard label="Taste Candidates" value={stats.candidates} />
        <StatCard label="Reco History" value={stats.history} />
      </section>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Recent Movies */}
        <section className="bg-zinc-800 rounded-lg p-4">
          <h2 className="text-xl font-semibold mb-4">📽️ Recent Movies</h2>
          {recentMovies && recentMovies.length > 0 ? (
            <ul className="space-y-2">
              {recentMovies.map((movie: Movie) => (
                <li key={movie.tmdb_id} className="p-2 bg-zinc-700 rounded">
                  <span className="font-medium">{movie.title}</span>
                  <span className="text-zinc-400 ml-2">({movie.release_year ?? 'N/A'})</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-zinc-500">No movies yet</p>
          )}
        </section>

        {/* Recent Interactions */}
        <section className="bg-zinc-800 rounded-lg p-4">
          <h2 className="text-xl font-semibold mb-4">⭐ Recent Interactions</h2>
          {recentInteractions && recentInteractions.length > 0 ? (
            <ul className="space-y-2">
              {recentInteractions.map((interaction: Interaction) => (
                <li key={interaction.id} className="p-2 bg-zinc-700 rounded text-sm">
                  <span>TMDB: {interaction.tmdb_id}</span>
                  {interaction.rating && <span className="ml-2">⭐ {interaction.rating}</span>}
                  {interaction.is_done && <span className="ml-2 text-green-400">✓ Done</span>}
                  {interaction.is_wishlisted && <span className="ml-2 text-yellow-400">♡ Wishlist</span>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-zinc-500">No interactions yet</p>
          )}
        </section>

        {/* Top Taste Candidates */}
        <section className="bg-zinc-800 rounded-lg p-4">
          <h2 className="text-xl font-semibold mb-4">🎯 Top Taste Candidates</h2>
          {topCandidates && topCandidates.length > 0 ? (
            <ul className="space-y-2">
              {topCandidates.map((candidate: TasteCandidate) => (
                <li key={candidate.id} className="p-2 bg-zinc-700 rounded flex justify-between">
                  <span>TMDB: {candidate.tmdb_id}</span>
                  <span className="text-green-400">{candidate.taste_score.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-zinc-500">No candidates yet</p>
          )}
        </section>
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-zinc-800 rounded-lg p-4 text-center">
      <p className="text-3xl font-bold">{value}</p>
      <p className="text-zinc-400 text-sm">{label}</p>
    </div>
  )
}
