import React from 'react';

interface StatCardProps {
    label: string;
    value: number;
    icon: string;
    gradient: string;
}

export function StatCard({ label, value, icon, gradient }: StatCardProps) {
    return (
        <div className={`relative overflow-hidden bg-zinc-900 border border-zinc-800 rounded-2xl p-6 transition-all hover:border-zinc-700 group`}>
            <div className={`absolute top-0 right-0 w-32 h-32 bg-gradient-to-br ${gradient} opacity-5 blur-3xl group-hover:opacity-10 transition-opacity`} />

            <div className="relative z-10">
                <div className="text-2xl mb-2">{icon}</div>
                <div className="text-4xl font-black text-white tracking-tighter mb-1">
                    {value.toLocaleString()}
                </div>
                <div className="text-zinc-500 text-sm font-medium uppercase tracking-wider">
                    {label}
                </div>
            </div>
        </div>
    );
}

export function StatsGrid({ stats }: { stats: { movies: number, interactions: number, candidates: number } }) {
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            <StatCard
                label="Collection"
                value={stats.movies}
                icon="📽️"
                gradient="from-blue-500 to-cyan-500"
            />
            <StatCard
                label="Évaluations"
                value={stats.interactions}
                icon="⭐"
                gradient="from-amber-500 to-orange-500"
            />
            <StatCard
                label="IA Candidates"
                value={stats.candidates}
                icon="🧠"
                gradient="from-purple-500 to-indigo-500"
            />
        </div>
    );
}
