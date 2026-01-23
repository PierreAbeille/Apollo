import React from 'react';

interface StatCardProps {
    label: string;
    value: number;
    icon: string;
    gradient: string;
}

export function StatCard({ label, value, icon, gradient }: StatCardProps) {
    return (
        <div className={`relative overflow-hidden bg-base-200 border border-base-300 rounded-xl p-4 transition-all hover:border-zinc-700 shadow-sm`}>
            <div className="relative z-10">
                <div className="text-3xl font-black text-white tracking-tighter">
                    {value.toLocaleString()}
                </div>
                <div className="text-zinc-500 text-[10px] font-black uppercase tracking-[0.2em] mt-1">
                    {label}
                </div>
            </div>
        </div>
    );
}

export function StatsGrid({ stats }: { stats: { movies: number, interactions: number, candidates: number } }) {
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            <StatCard
                label="Films en Base"
                value={stats.movies}
                icon=""
                gradient=""
            />
            <StatCard
                label="Notes Utilisateur"
                value={stats.interactions}
                icon=""
                gradient=""
            />
            <StatCard
                label="Candidats IA"
                value={stats.candidates}
                icon=""
                gradient=""
            />
        </div>
    );
}
