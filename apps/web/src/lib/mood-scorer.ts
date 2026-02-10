/**
 * Mood Scorer - TypeScript port of Python mood_scorer.py
 * 
 * Computes mood-based scores using Plutchik's wheel of emotions.
 */

// =============================================================================
// TYPES
// =============================================================================

export type PrimaryEmotion =
    | 'joy'
    | 'trust'
    | 'fear'
    | 'surprise'
    | 'sadness'
    | 'disgust'
    | 'anger'
    | 'anticipation';

export type Dyad =
    // Primary dyads (combinations of adjacent emotions)
    | 'love'
    | 'submission'
    | 'awe'
    | 'disapproval'
    | 'remorse'
    | 'contempt'
    | 'aggressiveness'
    | 'optimism'
    // Intensity dyads (extreme versions)
    | 'ecstasy'
    | 'admiration'
    | 'terror'
    | 'amazement'
    | 'grief'
    | 'loathing'
    | 'rage'
    | 'vigilance';

export type Mood = PrimaryEmotion | Dyad;

export type Preset = 'congruence' | 'regulation' | 'stimulation';

export interface FilmEmotions {
    /** 8D emotion vector [joy, trust, fear, surprise, sadness, disgust, anger, anticipation] */
    e: number[];
    /** Confidence score (top1 - top2) */
    c: number;
}

export interface EmotionData {
    [tmdbId: string]: FilmEmotions;
}

// =============================================================================
// CONSTANTS
// =============================================================================

export const PRIMARY_ORDER: PrimaryEmotion[] = [
    'joy', 'trust', 'fear', 'surprise', 'sadness', 'disgust', 'anger', 'anticipation'
];

export const DYADS: Record<Dyad, [PrimaryEmotion, PrimaryEmotion]> = {
    // Primary dyads (first-degree combinations of adjacent emotions)
    love: ['joy', 'trust'],
    submission: ['trust', 'fear'],
    awe: ['fear', 'surprise'],
    disapproval: ['surprise', 'sadness'],
    remorse: ['sadness', 'disgust'],
    contempt: ['disgust', 'anger'],
    aggressiveness: ['anger', 'anticipation'],
    optimism: ['anticipation', 'joy'],
    // Intensity dyads (extreme versions)
    ecstasy: ['joy', 'anticipation'],
    admiration: ['joy', 'trust'],
    terror: ['trust', 'fear'],
    amazement: ['fear', 'surprise'],
    grief: ['surprise', 'sadness'],
    loathing: ['sadness', 'disgust'],
    rage: ['disgust', 'anger'],
    vigilance: ['anger', 'anticipation'],
};

// French names for UI
export const MOOD_NAMES_FR: Record<Mood, string> = {
    // Primaries
    joy: 'Joie',
    trust: 'Confiance',
    fear: 'Peur',
    surprise: 'Surprise',
    sadness: 'Tristesse',
    disgust: 'Dégoût',
    anger: 'Colère',
    anticipation: 'Anticipation',
    // Primary dyads (first-degree combinations)
    love: 'Amour',
    submission: 'Soumission',
    awe: 'Émerveillement',
    disapproval: 'Désapprobation',
    remorse: 'Remords',
    contempt: 'Mépris',
    aggressiveness: 'Aggressivité',
    optimism: 'Optimisme',
    // Intensity dyads
    ecstasy: 'Extase',
    admiration: 'Admiration',
    terror: 'Terreur',
    amazement: 'Étonnement',
    grief: 'Chagrin',
    loathing: 'Aversion',
    rage: 'Rage',
    vigilance: 'Vigilance',
};

export const MOOD_EMOJI: Record<Mood, string> = {
    joy: '😂', trust: '🤝', fear: '😱', surprise: '😲',
    sadness: '😢', disgust: '🤢', anger: '😡', anticipation: '🤔',
    love: '🥰', submission: '🙇', awe: '🤩', disapproval: '👎',
    remorse: '😓', contempt: '😒', aggressiveness: '😤', optimism: '🤞',
    ecstasy: '🤣', admiration: '😍', terror: '👹', amazement: '🤯',
    grief: '😭', loathing: '🤮', rage: '🤬', vigilance: '🧐',
};

export const PRESET_NAMES_FR: Record<Preset, string> = {
    congruence: 'Rester dans le mood',
    regulation: 'Me changer les idées',
    stimulation: 'Me réveiller',
};

// =============================================================================
// TRANSFORMATION MATRICES
// =============================================================================

type TransformationMatrix = Record<PrimaryEmotion, Record<PrimaryEmotion, number>>;

const T_CONGRUENCE: TransformationMatrix = {
    joy: { joy: 1, trust: 0, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    trust: { joy: 0, trust: 1, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    fear: { joy: 0, trust: 0, fear: 1, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    surprise: { joy: 0, trust: 0, fear: 0, surprise: 1, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    sadness: { joy: 0, trust: 0, fear: 0, surprise: 0, sadness: 1, disgust: 0, anger: 0, anticipation: 0 },
    disgust: { joy: 0, trust: 0, fear: 0, surprise: 0, sadness: 0, disgust: 1, anger: 0, anticipation: 0 },
    anger: { joy: 0, trust: 0, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 1, anticipation: 0 },
    anticipation: { joy: 0, trust: 0, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 1 },
};

const T_REGULATION: TransformationMatrix = {
    sadness: { joy: 0.6, trust: 0.4, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    fear: { joy: 0.4, trust: 0.6, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    disgust: { joy: 0.4, trust: 0.6, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    anger: { joy: 0.4, trust: 0.6, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    anticipation: { joy: 0.4, trust: 0.6, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    surprise: { joy: 0, trust: 0.5, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 0.5 },
    trust: { joy: 0.5, trust: 0, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 0.5 },
    joy: { joy: 0, trust: 0, fear: 0, surprise: 0.6, sadness: 0, disgust: 0, anger: 0, anticipation: 0.4 },
};

const T_STIMULATION: TransformationMatrix = {
    sadness: { joy: 0, trust: 0, fear: 0, surprise: 0.6, sadness: 0, disgust: 0, anger: 0, anticipation: 0.4 },
    fear: { joy: 0, trust: 0, fear: 0, surprise: 0.4, sadness: 0, disgust: 0, anger: 0, anticipation: 0.6 },
    disgust: { joy: 0.5, trust: 0, fear: 0, surprise: 0.5, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    anger: { joy: 0, trust: 0, fear: 0, surprise: 0.4, sadness: 0, disgust: 0, anger: 0, anticipation: 0.6 },
    anticipation: { joy: 0.4, trust: 0, fear: 0, surprise: 0.6, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    surprise: { joy: 0.6, trust: 0.4, fear: 0, surprise: 0, sadness: 0, disgust: 0, anger: 0, anticipation: 0 },
    trust: { joy: 0, trust: 0, fear: 0, surprise: 0.4, sadness: 0, disgust: 0, anger: 0, anticipation: 0.6 },
    joy: { joy: 0, trust: 0, fear: 0, surprise: 0.6, sadness: 0, disgust: 0, anger: 0, anticipation: 0.4 },
};


export const PRESETS: Record<Preset, TransformationMatrix> = {
    congruence: T_CONGRUENCE,
    regulation: T_REGULATION,
    stimulation: T_STIMULATION,
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Check if a mood is a primary emotion
 */
export function isPrimary(mood: string): mood is PrimaryEmotion {
    return PRIMARY_ORDER.includes(mood as PrimaryEmotion);
}

/**
 * Check if a mood is a dyad
 */
export function isDyad(mood: string): mood is Dyad {
    return mood in DYADS;
}

/**
 * Decompose mood into primary distribution
 */
export function moodToPrimaryDistribution(mood: Mood): Record<PrimaryEmotion, number> {
    const dist: Record<PrimaryEmotion, number> = {
        joy: 0, trust: 0, fear: 0, surprise: 0,
        sadness: 0, disgust: 0, anger: 0, anticipation: 0,
    };

    if (isPrimary(mood)) {
        dist[mood] = 1.0;
    } else if (isDyad(mood)) {
        const [a, b] = DYADS[mood];
        dist[a] = 0.5;
        dist[b] = 0.5;
    }

    return dist;
}

/**
 * Apply regulation interpolation to get target emotion vector
 * factor: 0.0 (congruence) to 1.0 (full regulation)
 */
export function getInterpolatedTarget(mood: Mood, factor: number): number[] {
    const moodDist = moodToPrimaryDistribution(mood);

    // E_target = Σ(mood_dist[p] × T_interpolated[p])
    // T_interpolated = (1-f)*T_cong + f*T_reg
    const target = PRIMARY_ORDER.map(() => 0);

    for (const primary of PRIMARY_ORDER) {
        const weight = moodDist[primary];
        if (weight > 0) {
            const rowCong = T_CONGRUENCE[primary];
            const rowReg = T_REGULATION[primary];

            PRIMARY_ORDER.forEach((emo, i) => {
                const valCong = rowCong[emo] ?? 0;
                const valReg = rowReg[emo] ?? 0;
                const mixed = (1 - factor) * valCong + factor * valReg;

                target[i] = (target[i] ?? 0) + weight * mixed;
            });
        }
    }

    // Normalize
    const sum = target.reduce((a, b) => a + b, 0);
    if (sum > 0) {
        return target.map(v => v / sum);
    }
    return target;
}


/**
 * Compute mood score for a film
 */
export function computeMoodScore(
    filmEmotions: number[],
    targetEmotions: number[],
    confidence: number,
    minConfidence: number = 0.1
): number {
    // Dot product
    const alignment = filmEmotions.reduce((sum, e, i) => sum + e * (targetEmotions[i] ?? 0), 0);

    // Weight by confidence
    const effectiveConf = Math.max(confidence, minConfidence);

    return alignment * effectiveConf;
}

/**
 * Get all moods (primaries + dyads)
 */
export function getAllMoods(): Mood[] {
    return [...PRIMARY_ORDER, ...Object.keys(DYADS) as Dyad[]];
}

// =============================================================================
// HELPER UTILS
// =============================================================================

/**
 * Find the dyad formed by two primary emotions
 */
export function getDyadFromPrimaries(p1: PrimaryEmotion, p2: PrimaryEmotion): Dyad | null {
    for (const [dyad, [a, b]] of Object.entries(DYADS)) {
        if ((a === p1 && b === p2) || (a === p2 && b === p1)) {
            return dyad as Dyad;
        }
    }
    return null;
}

export function getAllowedAdjacents(current: PrimaryEmotion): PrimaryEmotion[] {
    const idx = PRIMARY_ORDER.indexOf(current);
    const prev = (idx - 1 + 8) % 8;
    const next = (idx + 1) % 8;
    return [PRIMARY_ORDER[prev]!, current, PRIMARY_ORDER[next]!];
}

export type MatchLevel = 'none' | 'low' | 'medium' | 'high';

/**
 * Get match level based on mood score
 */
export function getMoodMatchLevel(score: number): MatchLevel {
    if (score >= 0.6) return 'high';
    if (score >= 0.3) return 'medium';
    if (score >= 0.1) return 'low';
    return 'none';
}

export const MATCH_LEVEL_LABELS: Record<MatchLevel, string> = {
    high: 'Correspond parfaitement',
    medium: 'Correspond bien',
    low: 'Correspond un peu',
    none: 'Pas de correspondance',
};

// =============================================================================
// RERANKING
// =============================================================================

export interface Candidate {
    tmdb_id: number;
    taste_score: number;
    [key: string]: unknown;
}

export interface RankedCandidate extends Candidate {
    mood_score: number;
    final_score: number;
    match_level: MatchLevel;
    mood_percentile: number;
}

/**
 * Intensity levels for mood filtering
 */
export type MoodIntensity = 'plutot' | 'beaucoup';

/**
 * UX Labels for mood match (never show raw percentages)
 */
export const MOOD_MATCH_LABELS = {
    un_peu: 'Correspond un peu à ton mood',
    bien: 'Correspond bien à ton mood',
    beaucoup: 'Correspond beaucoup à ton mood',
} as const;

export type MoodMatchLabel = keyof typeof MOOD_MATCH_LABELS;

/**
 * Get UX label based on percentile (within the filtered set)
 */
export function getMoodMatchLabel(percentile: number): MoodMatchLabel {
    if (percentile > 75) return 'beaucoup';
    if (percentile > 55) return 'bien';
    return 'un_peu';
}

/**
 * Rerank and filter candidates based on mood alignment
 * 
 * Architecture:
 * 1. Candidates are already Top N by taste_score (pre-filtered)
 * 2. Calculate mood_score for each
 * 3. Calculate mood_percentile (rank within this set)
 * 4. Filter by percentile threshold based on intensity
 * 5. Sort by mood_percentile DESC (best mood matches first)
 */
export function rerankWithMood<T extends Candidate>(
    candidates: T[],
    emotionData: EmotionData,
    mood: Mood,
    regulation: number = 0, // 0 to 100
    intensity: MoodIntensity = 'plutot'
): (T & { mood_score: number; mood_percentile: number; mood_label: MoodMatchLabel })[] {
    // Convert 0-100 to 0.0-1.0 factor, clamped
    const factor = Math.min(Math.max(regulation, 0), 100) / 100.0;
    const targetEmotions = getInterpolatedTarget(mood, factor);

    // Step 1: Calculate mood_score for each candidate
    const scored = candidates.map(candidate => {
        const emotions = emotionData[candidate.tmdb_id.toString()];
        let moodScore = 0;

        if (emotions) {
            moodScore = computeMoodScore(emotions.e, targetEmotions, emotions.c);
        }

        return {
            ...candidate,
            mood_score: moodScore,
        };
    });

    // Step 2: Calculate percentiles (rank-based, within this set)
    const sortedScores = scored.map(s => s.mood_score).sort((a, b) => a - b);

    const withPercentile = scored.map(item => {
        // Find rank position
        const rank = sortedScores.filter(s => s < item.mood_score).length;
        const percentile = (rank / sortedScores.length) * 100;

        return {
            ...item,
            mood_percentile: percentile,
            mood_label: getMoodMatchLabel(percentile),
        };
    });

    // Step 3: Filter by intensity threshold
    // "plutot" = top 66% (percentile >= 33)
    // "beaucoup" = top 33% (percentile >= 66)
    const threshold = intensity === 'beaucoup' ? 66 : 33;
    const filtered = withPercentile.filter(item => item.mood_percentile >= threshold);

    // Step 4: Sort by mood_percentile DESC (best matches first)
    return filtered.sort((a, b) => b.mood_percentile - a.mood_percentile);
}

/**
 * Get dominant emotion for a film
 */
export function getDominantEmotion(emotions: number[]): { emotion: PrimaryEmotion; score: number } {
    if (!emotions || emotions.length === 0) {
        return { emotion: 'joy', score: 0 };
    }

    let maxIdx = 0;
    let maxScore = emotions[0] ?? 0;

    for (let i = 1; i < emotions.length; i++) {
        const score = emotions[i] ?? 0;
        if (score > maxScore) {
            maxScore = score;
            maxIdx = i;
        }
    }

    return {
        emotion: PRIMARY_ORDER[maxIdx] ?? 'joy',
        score: maxScore,
    };
}
