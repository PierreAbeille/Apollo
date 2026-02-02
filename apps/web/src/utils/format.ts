/**
 * Formats a raw ML score into a readable percentage.
 * 
 * Logic:
 * - If score is 0-1 (legacy class probability), multiply by 100.
 * - If score is 1-10 (new regression model), multiply by 10.
 * 
 * @param score Raw score from the DB (double precision)
 * @returns Formatted percentage string (e.g. "85%")
 */
export function formatTasteScore(score: number | null | undefined): string {
    if (score === null || score === undefined) return '0%';

    // Detect if score is legacy (0-1) or new (1-10)
    // Actually, since we've transitioned, most scores will be > 1.
    // If it's very low (< 1), it might be a zero or a legacy score.
    // But since it's now a regression on 1-10, we'll assume 1-10 scale.

    let percentage: number;

    if (score <= 1.0) {
        // Legacy or very low score
        percentage = Math.round(score * 100);
    } else {
        // New regression score (1-10)
        percentage = Math.round(score * 10);
    }

    // Clamp to 100%
    return `${Math.min(100, Math.max(0, percentage))}%`;
}
