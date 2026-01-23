"""Build text representations for movie embeddings."""
from typing import Dict, List, Any, Optional


def build_text_for_embedding(
    overview: Optional[str],
    genres: List[str],
    keywords: List[str],
    cast: List[str],
    director: Optional[str],
    lang: str = "fr"
) -> str:
    """
    Build a rich text representation for semantic embedding.
    
    Concatenates all available movie metadata into a single string optimized
    for semantic similarity in French or English.
    
    Args:
        overview: Movie plot overview/synopsis
        genres: List of genre names
        keywords: List of TMDB keywords
        cast: List of actor names (top 8 recommended)
        director: Director name
        lang: Language code ('fr' or 'en')
        
    Returns:
        Concatenated text string ready for embedding
    """
    parts = []
    
    # Overview (most important semantic signal)
    if overview:
        parts.append(overview.strip())
    
    # Genres (strong categorical signal)
    if genres:
        genre_text = "Genres: " + ", ".join(genres) if lang == "en" else "Genres: " + ", ".join(genres)
        parts.append(genre_text)
    
    # Director (auteur signal)
    if director:
        director_text = f"Director: {director}" if lang == "en" else f"Réalisateur: {director}"
        parts.append(director_text)
    
    # Cast (collaborative filtering signal)
    if cast:
        # Limit to top 8 to avoid noise
        top_cast = cast[:8]
        cast_text = "Cast: " + ", ".join(top_cast) if lang == "en" else "Avec: " + ", ".join(top_cast)
        parts.append(cast_text)
    
    # Keywords (thematic signal)
    if keywords:
        # Limit keywords to avoid overwhelming the text
        top_keywords = keywords[:15]
        keyword_text = "Keywords: " + ", ".join(top_keywords) if lang == "en" else "Mots-clés: " + ", ".join(top_keywords)
        parts.append(keyword_text)
    
    # Join with double newline for clear separation
    return "\n\n".join(parts)


def extract_movie_metadata(tmdb_details: Dict[str, Any], tmdb_credits: Dict[str, Any], tmdb_keywords: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant metadata from TMDB API responses.
    
    Args:
        tmdb_details: Response from /movie/{id}
        tmdb_credits: Response from /movie/{id}/credits
        tmdb_keywords: Response from /movie/{id}/keywords
        
    Returns:
        Dictionary with extracted metadata
    """
    # Extract genres
    genres = [g["name"] for g in tmdb_details.get("genres", [])]
    
    # Extract keywords
    keywords = [kw["name"] for kw in tmdb_keywords.get("keywords", [])]
    
    # Extract cast (top by order)
    cast_list = tmdb_credits.get("cast", [])
    cast = [actor["name"] for actor in cast_list[:8]]
    
    # Extract director
    crew_list = tmdb_credits.get("crew", [])
    director = None
    for person in crew_list:
        if person.get("job") == "Director":
            director = person["name"]
            break
    
    # Overview
    overview = tmdb_details.get("overview", "")
    
    return {
        "overview": overview,
        "genres": genres,
        "keywords": keywords,
        "cast": cast,
        "crew": [{"name": director, "job": "Director"}] if director else [],
        "director": director,
    }
