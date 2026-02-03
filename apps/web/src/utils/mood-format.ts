
/**
 * Formats a raw mood similarity score into a 1-10 string.
 * Logic: User wants 50% (0.5) to be a 10/10.
 * Formula: min(10, Math.round((score / 0.5) * 10))
 */
export function formatMoodScore(score: number): string {
    if (score === undefined || score === null) return '0/10';
    const scaled = Math.min(10, Math.round((score / 0.5) * 10));
    return `${scaled}/10`;
}
