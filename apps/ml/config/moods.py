"""Mood definitions for semantic filtering.

Each mood has a rich description to generate quality embeddings.
"""

MOODS = [
    {
        "id": "mind_bending",
        "name": "Retourne le cerveau",
        "description": "Mind-bending, philosophie, paradoxe temporel, narration complexe, thriller psychologique, puzzle mental, réalité simulée, twist final choquant, intellectuellement stimulant. Films comme Inception, Matrix, Shutter Island, Tenet."
    },
    {
        "id": "feel_good",
        "name": "Ça fait du bien",
        "description": "Feel-good, optimiste, réconfortant, inspirant, wholesome, humaniste, joie de vivre, espoir, chaleur humaine, personnages attachants. Films comme Intouchables, Amélie Poulain, Green Book, Paddington."
    },
    {
        "id": "dark_gritty",
        "name": "Sombre & Réaliste",
        "description": "Dark, gritty, noirceur, violence réaliste, corruption, moralement ambigu, atmosphère pesante, thriller urbain, sans concession, désespéré. Films comme Joker, Se7en, Taxi Driver, Prisoners."
    },
    {
        "id": "tension",
        "name": "Tension pure",
        "description": "Edge of your seat, suspense insoutenable, stress, survie, course contre la montre, angoisse, cloué au siège, adrénaline de survie. Films comme Mad Max: Fury Road, Whiplash, A Quiet Place, Gravity."
    },
    {
        "id": "surreal",
        "name": "Onirique & Étrange",
        "description": "Surréalisme, rêve, poésie visuelle, atmosphère étrange, abstrait, artistique, mélancolie douce, voyage spirituel, hallucinatoire. Films comme Spirited Away, Mulholland Drive, Eternal Sunshine of the Spotless Mind, The Grand Budapest Hotel."
    },
    {
        "id": "epic",
        "name": "Grand Spectacle",
        "description": "Épique, grandiose, enjeux colossaux, batailles massives, mythes, légendes, orchestral, visuellement époustouflant, scale immense. Films comme Dune, Lord of the Rings, Gladiator, Avatar."
    },
    {
        "id": "intimate",
        "name": "Intimiste & Calme",
        "description": "Intimiste, étude de caractère, lent, contemplatif, dialogue, relations humaines subtiles, réalisme émotionnel, calme, slice of life. Films comme Lost in Translation, Her, Past Lives, Moonlight."
    },
    {
        "id": "nostalgia",
        "name": "Nostalgie",
        "description": "Nostalgie, rétro, années 80, enfance, coming of age, souvenirs, mélancolie du passé, esthétique vintage, innocence perdue. Films comme Stranger Things, La La Land, Super 8, Stand by Me."
    },
    {
        "id": "disturbing",
        "name": "Dérangeant & Viscéral",
        "description": "Dérangeant, choc, horreur psychologique, malaise, violence graphique, traumatisme, peur viscérale, cauchemar, provocalteur. Films comme Midsommar, Requiem for a Dream, Parasite."
    }
]


def get_mood_by_id(mood_id: str) -> dict | None:
    """Get a mood by its ID."""
    for mood in MOODS:
        if mood["id"] == mood_id:
            return mood
    return None


def get_all_mood_texts() -> list[tuple[str, str]]:
    """Get all moods as (id, text_for_embedding) tuples."""
    return [(m["id"], f"{m['name']}. {m['description']}") for m in MOODS]
