"""Mood definitions for semantic filtering.

Each mood has a rich description to generate quality embeddings.
"""

MOODS = [
    {
        "id": "adrenaline",
        "name": "Besoin d'adrénaline",
        "description": "Action explosive, courses-poursuites intenses, combats spectaculaires, cascades impressionnantes, tension extrême, adrénaline pure, rythme effréné"
    },
    {
        "id": "adventure",
        "name": "Évasion & Aventure",
        "description": "Voyages épiques, exploration de nouveaux mondes, découverte, quêtes héroïques, périples extraordinaires, horizons lointains, aventures palpitantes"
    },
    {
        "id": "animation",
        "name": "Un peu de magie",
        "description": "Animation féerique, mondes enchantés, imaginaire enfantin, dessins animés, magie visuelle, émerveillement, poésie animée"
    },
    {
        "id": "comedy",
        "name": "Besoin de rire",
        "description": "Comédie hilarante, humour absurde, situations comiques, gags, rire aux éclats, légèreté, bonne humeur contagieuse"
    },
    {
        "id": "crime",
        "name": "Thriller & Polar",
        "description": "Enquête policière, crime organisé, détective, suspense criminel, polar noir, investigation, mystères sombres, gangsters"
    },
    {
        "id": "documentary",
        "name": "Apprendre quelque chose",
        "description": "Documentaire instructif, exploration du réel, découverte, culture, histoire vraie, savoir, connaissance, reportage captivant"
    },
    {
        "id": "drama",
        "name": "Émotion & Drame",
        "description": "Drame profond, émotion intense, histoires humaines touchantes, larmes, sensibilité, parcours de vie, tragédie, mélancolie"
    },
    {
        "id": "family",
        "name": "En famille",
        "description": "Film familial, tous âges, valeurs familiales, moments partagés, douceur, bienveillance, aventures pour enfants et parents"
    },
    {
        "id": "fantasy",
        "name": "Mondes imaginaires",
        "description": "Fantasy épique, créatures magiques, royaumes enchantés, elfes et dragons, quêtes mythiques, univers fantastiques, magie et sortilèges"
    },
    {
        "id": "history",
        "name": "Histoire & Passé",
        "description": "Film historique, reconstitution d'époque, passé glorieux, grandes batailles, personnages historiques, fresque temporelle, mémoire collective"
    },
    {
        "id": "horror",
        "name": "Frisson & Horreur",
        "description": "Horreur terrifiante, frissons glacés, peur viscérale, créatures monstrueuses, atmosphère angoissante, épouvante, cauchemar éveillé"
    },
    {
        "id": "music",
        "name": "Musique & Rythme",
        "description": "Film musical, chansons entraînantes, danse, rythme, mélodies, concerts, ambiance festive, comédie musicale"
    },
    {
        "id": "mystery",
        "name": "Mystère & Enquête",
        "description": "Mystère intrigant, énigmes à résoudre, secrets cachés, révélations surprenantes, suspense psychologique, puzzle narratif"
    },
    {
        "id": "romance",
        "name": "Amour & Romance",
        "description": "Romance passionnée, histoire d'amour, sentiments profonds, passion amoureuse, coup de foudre, tendresse, relations intimes"
    },
    {
        "id": "scifi",
        "name": "Futur & SF",
        "description": "Science-fiction futuriste, technologie avancée, voyages spatiaux, intelligence artificielle, dystopie, exploration spatiale, univers high-tech"
    },
    {
        "id": "thriller",
        "name": "Suspense total",
        "description": "Thriller haletant, tension permanente, suspense insoutenable, retournements de situation, danger imminent, course contre la montre"
    },
    {
        "id": "war",
        "name": "Guerre & Conflit",
        "description": "Film de guerre, batailles épiques, soldats héroïques, conflits armés, sacrifice, fraternité militaire, horreurs de la guerre"
    },
    {
        "id": "western",
        "name": "Cowboys & Western",
        "description": "Western classique, cowboys, duels au soleil, Far West, chevaux et désert, hors-la-loi, shérif, frontière américaine"
    },
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
