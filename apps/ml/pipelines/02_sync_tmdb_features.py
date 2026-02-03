#!/usr/bin/env python3
"""
Pipeline 02: Sync TMDB Features

Fetches detailed metadata from TMDB for each movie and populates the
movie_features table with genres, keywords, cast, crew, and text_for_embedding.
"""
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import TMDB_RATE_LIMIT_DELAY, TMDB_MAX_RETRIES
from clients.tmdb import get_movie_details, get_movie_credits, get_movie_keywords
from clients.db import DatabaseClient
from features.text_builder import extract_movie_metadata, build_text_for_embedding


class TMDBFeatureSync:
    """Syncs TMDB metadata to movie_features table."""
    
    def __init__(self, lang: str = "en"):
        """
        Initialize syncer.
        
        Args:
            lang: Language for TMDB data ('en' recommended, UI will be in French)
        """
        self.lang = lang
        self.db = DatabaseClient()
        
        # Statistics
        self.stats = {
            "total": 0,
            "synced": 0,
            "skipped": 0,
            "errors": 0,
            "api_calls": 0,
        }
    
    def fetch_movie_data(self, tmdb_id: int) -> Dict[str, Any] | None:
        """
        Fetch all required TMDB data for a movie.
        
        Args:
            tmdb_id: TMDB movie ID
            
        Returns:
            Dictionary with all metadata or None on error
        """
        try:
            # Fetch details
            print(f"  📡 Fetching details...", end="", flush=True)
            time.sleep(TMDB_RATE_LIMIT_DELAY)
            details = get_movie_details(tmdb_id, language=f"{self.lang}-{self.lang.upper()}")
            self.stats["api_calls"] += 1
            
            # Fetch credits
            print(f" credits...", end="", flush=True)
            time.sleep(TMDB_RATE_LIMIT_DELAY)
            credits = get_movie_credits(tmdb_id)
            self.stats["api_calls"] += 1
            
            # Fetch keywords
            print(f" keywords...", end="", flush=True)
            time.sleep(TMDB_RATE_LIMIT_DELAY)
            keywords = get_movie_keywords(tmdb_id)
            self.stats["api_calls"] += 1
            
            print(" ✓")
            
            return {
                "details": details,
                "credits": credits,
                "keywords": keywords,
            }
            
        except Exception as e:
            print(f" ✗ Error: {e}")
            self.stats["errors"] += 1
            return None
    
    def process_movie(self, movie: Dict[str, Any]) -> bool:
        """
        Process a single movie.
        
        Args:
            movie: Movie record from database
            
        Returns:
            True if successfully processed
        """
        tmdb_id = movie["tmdb_id"]
        title = movie["title"]
        
        print(f"\n[{self.stats['total'] + 1}] {title} (ID: {tmdb_id})")
        
        # Fetch TMDB data
        tmdb_data = self.fetch_movie_data(tmdb_id)
        if not tmdb_data:
            return False
        
        # Extract metadata
        metadata = extract_movie_metadata(
            tmdb_data["details"],
            tmdb_data["credits"],
            tmdb_data["keywords"]
        )
        
        # Build text for embedding
        text = build_text_for_embedding(
            overview=metadata["overview"],
            genres=metadata["genres"],
            keywords=metadata["keywords"],
            cast=metadata["cast"],
            director=metadata["director"],
            lang=self.lang
        )
        
        print(f"  📝 Text length: {len(text)} chars")
        print(f"  🎬 Genres: {', '.join(metadata['genres'][:3]) if metadata['genres'] else 'None'}")
        print(f"  👥 Cast: {', '.join(metadata['cast'][:3]) if metadata['cast'] else 'None'}")
        
        # Upsert to database
        try:
            self.db.upsert_movie_features(
                tmdb_id=tmdb_id,
                lang=self.lang,
                overview=metadata["overview"],
                keywords=tmdb_data["keywords"].get("keywords", []),
                genres=tmdb_data["details"].get("genres", []),
                cast=tmdb_data["credits"].get("cast", [])[:8],
                crew=metadata["crew"],
                production_countries=metadata["production_countries"],
                popularity=metadata["popularity"],
                vote_average=metadata["vote_average"],
                vote_count=metadata["vote_count"],
                text_for_embedding=text
            )
            
            print(f"  ✓ Synced to database")
            self.stats["synced"] += 1
            return True
            
        except Exception as e:
            print(f"  ✗ Database error: {e}")
            self.stats["errors"] += 1
            return False
    
    def run(self):
        """Main sync process."""
        print("=" * 60)
        print(f"Pipeline 02: Sync TMDB Features (Language: {self.lang})")
        print("=" * 60)
        
        # Connect to database
        self.db.connect()
        
        # Get movies without features or missing Phase 12 data
        # We check for movies where production_countries is NULL as proxy for missing newest data
        query = """
            SELECT m.*
            FROM movies m
            LEFT JOIN movie_features mf ON m.tmdb_id = mf.tmdb_id
            WHERE mf.tmdb_id IS NULL OR mf.production_countries IS NULL
            ORDER BY m.tmdb_id
        """
        movies = self.db.fetch_all(query)
        total_movies = len(movies)
        
        if total_movies == 0:
            print(f"\\n✓ All movies already have {self.lang} features and Phase 12 data!")
            self.db.close()
            return
        
        print(f"\nFound {total_movies} movies without {self.lang} features")
        print(f"Estimated API calls: {total_movies * 3}")
        print(f"Estimated time: ~{total_movies * 3 * TMDB_RATE_LIMIT_DELAY / 60:.1f} minutes")
        
        # Process each movie
        for movie in movies:
            self.stats["total"] += 1
            self.process_movie(movie)
        
        # Close database
        self.db.close()
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total movies:      {self.stats['total']}")
        print(f"✓ Synced:          {self.stats['synced']}")
        print(f"✗ Errors:          {self.stats['errors']}")
        print(f"📡 TMDB API calls: {self.stats['api_calls']}")
        print("=" * 60)


if __name__ == "__main__":
    # Default to English for data (French only for UI)
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    
    if lang not in ["fr", "en"]:
        print(f"Error: Invalid language '{lang}'. Use 'fr' or 'en'.")
        print("Note: 'en' is recommended - French is for UI only")
        sys.exit(1)
    
    syncer = TMDBFeatureSync(lang=lang)
    syncer.run()
