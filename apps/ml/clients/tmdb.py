import os
import requests
from dotenv import load_dotenv

# Load environment variables
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_READ_ACCESS_TOKEN = os.getenv("TMDB_API_READ_ACCESS_TOKEN")
TMDB_BASE_URL = "https://api.themoviedb.org/3"


def get_headers():
    """Returns headers for TMDb API requests using Bearer token."""
    return {
        "Authorization": f"Bearer {TMDB_READ_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }


def search_movie(query: str, language: str = "fr-FR"):
    """Search for a movie by title."""
    url = f"{TMDB_BASE_URL}/search/movie"
    params = {
        "query": query,
        "language": language
    }
    response = requests.get(url, headers=get_headers(), params=params)
    response.raise_for_status()
    return response.json()


def get_movie_details(movie_id: int, language: str = "fr-FR"):
    """Get detailed information about a movie."""
    url = f"{TMDB_BASE_URL}/movie/{movie_id}"
    params = {"language": language}
    response = requests.get(url, headers=get_headers(), params=params)
    response.raise_for_status()
    return response.json()


def get_movie_credits(movie_id: int):
    """Get cast and crew for a movie."""
    url = f"{TMDB_BASE_URL}/movie/{movie_id}/credits"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()


def get_popular_movies(language: str = "fr-FR", page: int = 1):
    """Get a list of popular movies."""
    url = f"{TMDB_BASE_URL}/movie/popular"
    params = {"language": language, "page": page}
    response = requests.get(url, headers=get_headers(), params=params)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # Quick test
    print("Testing TMDb API connection...")
    
    if not TMDB_READ_ACCESS_TOKEN:
        print("ERROR: TMDB_API_READ_ACCESS_TOKEN not found in environment")
        exit(1)
    
    try:
        result = search_movie("Inception")
        if result.get("results"):
            movie = result["results"][0]
            print(f"✓ Connection successful!")
            print(f"  Found: {movie['title']} ({movie.get('release_date', 'N/A')[:4]})")
            print(f"  Vote: {movie['vote_average']}/10")
        else:
            print("Connection OK but no results found.")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
