"""Emotion definitions based on Plutchik's wheel of emotions.

8 Primary emotions + 8 Dyads (combinations).
3 Transformation matrices for mood-based recommendations.
"""

from typing import Dict, List, Tuple, Optional


# =============================================================================
# PRIMARY EMOTIONS (8)
# =============================================================================
# Anchors: sensory/emotional vocabulary + rhythm, NO themes/tropes

PRIMARY_EMOTIONS = {
    "joy": {
        "id": "joy",
        "name_fr": "Joie",
        "anchor": (
            "Warm, uplifting, playful, light-hearted. "
            "Makes you smile and feel good. "
            "Cozy humor, gentle optimism, easy to watch."
        ),
    },
    "trust": {
        "id": "trust",
        "name_fr": "Confiance",
        "anchor": (
            "Safe, reassuring, comforting. "
            "A sense of trust, stability, and warmth. "
            "Calm tone, supportive relationships, grounded and secure."
        ),
    },
    "fear": {
        "id": "fear",
        "name_fr": "Peur",
        "anchor": (
            "Dread, anxiety, feeling unsafe. "
            "Sustained tension, looming threat, tight atmosphere. "
            "Makes you uneasy and on edge."
        ),
    },
    "surprise": {
        "id": "surprise",
        "name_fr": "Surprise",
        "anchor": (
            "Unpredictable, constantly shifting. "
            "Twists in tone, sudden changes, unexpected moments. "
            "Keeps you guessing and reacting."
        ),
    },
    "sadness": {
        "id": "sadness",
        "name_fr": "Tristesse",
        "anchor": (
            "Melancholic, heavy-hearted, emotionally raw. "
            "Bittersweet, tender, cathartic. "
            "Leaves a lingering ache."
        ),
    },
    "disgust": {
        "id": "disgust",
        "name_fr": "Dégoût",
        "anchor": (
            "Repulsion, discomfort, something feels wrong. "
            "Creeping unease, ugliness, moral or visceral disgust. "
            "Makes you want to look away."
        ),
    },
    "anger": {
        "id": "anger",
        "name_fr": "Colère",
        "anchor": (
            "Intense frustration, outrage, aggression. "
            "Confrontational, explosive, high heat. "
            "Feels like pressure building and release."
        ),
    },
    "anticipation": {
        "id": "anticipation",
        "name_fr": "Anticipation",
        "anchor": (
            "Excitement, forward pull, curiosity. "
            "Builds momentum, suspense, expectation. "
            "Makes you lean in and want to know what happens next."
        ),
    },
}

# Ordered list for vector indexing
PRIMARY_ORDER = ["joy", "trust", "fear", "surprise", "sadness", "disgust", "anger", "anticipation"]


# =============================================================================
# DYADS (8) - Combinations of adjacent primaries on Plutchik's wheel
# =============================================================================

DYADS = {
    "ecstasy": ("joy", "anticipation"),       # Extase
    "admiration": ("joy", "trust"),           # Admiration
    "terror": ("trust", "fear"),              # Terreur
    "amazement": ("fear", "surprise"),        # Étonnement
    "grief": ("surprise", "sadness"),         # Chagrin
    "loathing": ("sadness", "disgust"),       # Aversion
    "rage": ("disgust", "anger"),             # Rage
    "vigilance": ("anger", "anticipation"),   # Vigilance
}

DYAD_NAMES_FR = {
    "ecstasy": "Extase",
    "admiration": "Admiration",
    "terror": "Terreur",
    "amazement": "Étonnement",
    "grief": "Chagrin",
    "loathing": "Aversion",
    "rage": "Rage",
    "vigilance": "Vigilance",
}


# =============================================================================
# TRANSFORMATION MATRICES (3 presets)
# =============================================================================
# Maps: user's current mood → target film emotions
# Each row sums to 1.0

T_CONGRUENCE: Dict[str, Dict[str, float]] = {
    # Identity matrix - stay in the mood
    "joy": {"joy": 1.0},
    "trust": {"trust": 1.0},
    "fear": {"fear": 1.0},
    "surprise": {"surprise": 1.0},
    "sadness": {"sadness": 1.0},
    "disgust": {"disgust": 1.0},
    "anger": {"anger": 1.0},
    "anticipation": {"anticipation": 1.0},
}

T_REGULATION: Dict[str, Dict[str, float]] = {
    # Goal: comfort, move toward trust + joy (soothe/regulate)
    "sadness": {"joy": 0.6, "trust": 0.4},
    "fear": {"trust": 0.6, "joy": 0.4},
    "disgust": {"trust": 0.6, "joy": 0.4},
    "anger": {"trust": 0.6, "joy": 0.4},
    "anticipation": {"trust": 0.6, "joy": 0.4},  # rumination → reassurance
    "surprise": {"trust": 0.5, "anticipation": 0.5},  # regain control
    "trust": {"joy": 0.5, "anticipation": 0.5},  # safe novelty
    "joy": {"surprise": 0.6, "anticipation": 0.4},  # safe novelty
}

T_STIMULATION: Dict[str, Dict[str, float]] = {
    # Goal: increase arousal → surprise + anticipation
    "sadness": {"surprise": 0.6, "anticipation": 0.4},
    "fear": {"anticipation": 0.6, "surprise": 0.4},  # controlled tension
    "disgust": {"surprise": 0.5, "joy": 0.5},  # reset/distraction
    "anger": {"anticipation": 0.6, "surprise": 0.4},  # channel into movement
    "anticipation": {"surprise": 0.6, "joy": 0.4},  # break rumination
    "surprise": {"joy": 0.6, "trust": 0.4},  # payoff/aftercare
    "trust": {"anticipation": 0.6, "surprise": 0.4},
    "joy": {"surprise": 0.6, "anticipation": 0.4},
}

PRESETS = {
    "congruence": T_CONGRUENCE,
    "regulation": T_REGULATION,
    "stimulation": T_STIMULATION,
}

PRESET_NAMES_FR = {
    "congruence": "Rester dans le mood",
    "regulation": "Me changer les idées",
    "stimulation": "Me réveiller",
}


# =============================================================================
# PARAMETERS
# =============================================================================

EMOTION_TEMPERATURE = 0.07  # τ for softmax (lower = more contrasty)
MOOD_ALPHA = 0.2  # Weight of mood_score in final ranking
MIN_CONFIDENCE = 0.1  # Threshold to consider a film "typed"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def mood_to_primary_distribution(mood: str) -> Dict[str, float]:
    """
    Convert any mood (primary or dyad) to a distribution over primaries.
    
    Primaries → 100% on that primary
    Dyads → 50/50 split on the two component primaries
    """
    if mood in PRIMARY_EMOTIONS:
        return {mood: 1.0}
    
    if mood in DYADS:
        a, b = DYADS[mood]
        return {a: 0.5, b: 0.5}
    
    raise ValueError(f"Unknown mood: {mood}. Must be primary or dyad.")


def apply_transformation(
    mood: str, 
    preset: str = "congruence"
) -> Dict[str, float]:
    """
    Apply transformation matrix to get target emotion distribution.
    
    Args:
        mood: Primary emotion or dyad (e.g., "sadness", "ecstasy")
        preset: One of "congruence", "regulation", "stimulation"
        
    Returns:
        Target distribution over 8 primaries (sums to 1.0)
    """
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset: {preset}")
    
    T = PRESETS[preset]
    
    # Decompose mood into primaries
    mood_dist = mood_to_primary_distribution(mood)
    
    # Apply transformation: E_target = Σ(mood_dist[p] × T[p])
    target = {p: 0.0 for p in PRIMARY_ORDER}
    
    for primary, weight in mood_dist.items():
        if primary in T:
            for target_emotion, target_weight in T[primary].items():
                target[target_emotion] += weight * target_weight
    
    # Normalize (should already sum to 1, but safety check)
    total = sum(target.values())
    if total > 0:
        target = {k: v / total for k, v in target.items()}
    
    return target


def get_all_moods() -> List[str]:
    """Get all available moods (8 primaries + 8 dyads)."""
    return list(PRIMARY_EMOTIONS.keys()) + list(DYADS.keys())


def get_mood_name_fr(mood: str) -> str:
    """Get French name for a mood."""
    if mood in PRIMARY_EMOTIONS:
        return PRIMARY_EMOTIONS[mood]["name_fr"]
    if mood in DYADS:
        return DYAD_NAMES_FR[mood]
    return mood


def get_anchor_texts() -> List[Tuple[str, str]]:
    """Get all anchors as (emotion_id, anchor_text) tuples for embedding."""
    return [(emo, data["anchor"]) for emo, data in PRIMARY_EMOTIONS.items()]


# =============================================================================
# TESTS
# =============================================================================

def test_mood_to_primary():
    """Test primary decomposition."""
    assert mood_to_primary_distribution("joy") == {"joy": 1.0}
    assert mood_to_primary_distribution("ecstasy") == {"joy": 0.5, "anticipation": 0.5}
    print("✓ test_mood_to_primary passed")


def test_apply_transformation():
    """Test transformation matrices."""
    # Congruence: identity
    target = apply_transformation("sadness", "congruence")
    assert target["sadness"] == 1.0
    
    # Regulation: sadness → joy + trust
    target = apply_transformation("sadness", "regulation")
    assert target["joy"] == 0.6
    assert target["trust"] == 0.4
    
    # Dyad + regulation
    target = apply_transformation("grief", "regulation")  # grief = surprise + sadness
    # 50% surprise → trust/anticipation, 50% sadness → joy/trust
    assert target["joy"] > 0
    assert target["trust"] > 0
    print("✓ test_apply_transformation passed")


def test_all_moods():
    """Test all moods list."""
    moods = get_all_moods()
    assert len(moods) == 16
    assert "joy" in moods
    assert "ecstasy" in moods
    print("✓ test_all_moods passed")


def run_all_tests():
    """Run all tests."""
    print("\n🧪 Running emotion config tests...\n")
    test_mood_to_primary()
    test_apply_transformation()
    test_all_moods()
    print("\n✅ All tests passed!\n")


if __name__ == "__main__":
    run_all_tests()
