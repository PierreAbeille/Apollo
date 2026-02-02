"""Database client wrapper using psycopg2."""
from utils.database import get_connection
from typing import List, Dict, Any, Optional
import psycopg2.extras


class DatabaseClient:
    """Wrapper for database operations."""
    
    def __init__(self):
        """Initialize database client."""
        self.conn = None
    
    def connect(self):
        """Establish database connection."""
        self.conn = get_connection()
        if not self.conn:
            raise ConnectionError("Failed to connect to database")
        return self
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def execute(self, query: str, params: tuple = None) -> None:
        """
        Execute a query without returning results.
        
        Args:
            query: SQL query
            params: Query parameters
        """
        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        self.conn.commit()
        cursor.close()
    
    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row as a dictionary.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Dictionary of column: value or None
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, params or ())
        result = cursor.fetchone()
        cursor.close()
        return dict(result) if result else None
    
    def fetch_all(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        Fetch all rows as dictionaries.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            List of dictionaries
        """
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in results]
    
    def upsert_movie(self, tmdb_id: int, title: str, release_year: Optional[int], poster_path: Optional[str]) -> None:
        """
        Insert or update a movie record.
        
        Args:
            tmdb_id: TMDB movie ID
            title: Movie title
            release_year: Release year
            poster_path: TMDB poster path
        """
        query = """
            INSERT INTO movies (tmdb_id, title, release_year, poster_path, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (tmdb_id) 
            DO UPDATE SET 
                title = EXCLUDED.title,
                release_year = EXCLUDED.release_year,
                poster_path = EXCLUDED.poster_path,
                updated_at = NOW()
        """
        self.execute(query, (tmdb_id, title, release_year, poster_path))
    
    def upsert_interaction(
        self, 
        tmdb_id: int, 
        rating: Optional[float] = None,
        is_done: bool = False,
        is_wishlisted: bool = False,
        is_recommended: bool = False,
        source: str = "letterboxd"
    ) -> None:
        """
        Insert or update an interaction record.
        
        Args:
            tmdb_id: TMDB movie ID
            rating: User rating (1-10)
            is_done: Whether movie has been watched
            is_wishlisted: Whether movie is in wishlist
            is_recommended: Whether movie is recommended by user
            source: Source of interaction ('letterboxd' or 'app')
        """
        # First check if interaction exists
        existing = self.fetch_one(
            "SELECT id FROM interactions WHERE tmdb_id = %s AND source = %s",
            (tmdb_id, source)
        )
        
        if existing:
            # Update existing
            query = """
                UPDATE interactions 
                SET rating = %s, is_done = %s, is_wishlisted = %s, is_recommended = %s, created_at = NOW()
                WHERE id = %s
            """
            self.execute(query, (rating, is_done, is_wishlisted, is_recommended, existing["id"]))
        else:
            # Insert new
            query = """
                INSERT INTO interactions (tmdb_id, rating, is_done, is_wishlisted, is_recommended, source, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            self.execute(query, (tmdb_id, rating, is_done, is_wishlisted, is_recommended, source))

    
    def get_movie_by_tmdb_id(self, tmdb_id: int) -> Optional[Dict[str, Any]]:
        """
        Get movie by TMDB ID.
        
        Args:
            tmdb_id: TMDB movie ID
            
        Returns:
            Movie record or None
        """
        query = "SELECT * FROM movies WHERE tmdb_id = %s"
        return self.fetch_one(query, (tmdb_id,))
    
    def get_all_interactions(self) -> List[Dict[str, Any]]:
        """
        Get all user interactions.
        
        Returns:
            List of interaction records
        """
        query = "SELECT * FROM interactions ORDER BY created_at DESC"
        return self.fetch_all(query)
    
    def upsert_movie_features(
        self,
        tmdb_id: int,
        lang: str,
        overview: Optional[str] = None,
        keywords: Optional[list] = None,
        genres: Optional[list] = None,
        cast: Optional[list] = None,
        crew: Optional[list] = None,
        text_for_embedding: Optional[str] = None
    ) -> None:
        """
        Insert or update movie features.
        
        Args:
            tmdb_id: TMDB movie ID
            lang: Language code ('fr' or 'en')
            overview: Movie overview/synopsis
            keywords: List of keyword dicts with 'id' and 'name'
            genres: List of genre dicts with 'id' and 'name'
            cast: List of cast member dicts
            crew: List of crew member dicts
            text_for_embedding: Pre-built text for embedding
        """
        import json
        
        # Default to English for all data
        if not lang:
            lang = "en"
        
        query = """
            INSERT INTO movie_features (
                tmdb_id, lang, overview, keywords, genres, \"cast\", \"crew\", text_for_embedding, tmdb_fetched_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (tmdb_id)
            DO UPDATE SET
                lang = EXCLUDED.lang,
                overview = EXCLUDED.overview,
                keywords = EXCLUDED.keywords,
                genres = EXCLUDED.genres,
                \"cast\" = EXCLUDED.\"cast\",
                \"crew\" = EXCLUDED.\"crew\",
                text_for_embedding = EXCLUDED.text_for_embedding,
                tmdb_fetched_at = NOW()
        """
        
        self.execute(query, (
            tmdb_id,
            lang,
            overview,
            json.dumps(keywords or []),
            json.dumps(genres or []),
            json.dumps(cast or []),
            json.dumps(crew or []),
            text_for_embedding
        ))
    
    def get_movies_without_features(self, lang: str = "en") -> List[Dict[str, Any]]:
        """
        Get movies that don't have features yet.
        
        Args:
            lang: Language code (kept for backwards compatibility, but ignored)
            
        Returns:
            List of movie records without features
        """
        query = """
            SELECT m.*
            FROM movies m
            LEFT JOIN movie_features mf ON m.tmdb_id = mf.tmdb_id
            WHERE mf.tmdb_id IS NULL
            ORDER BY m.tmdb_id
        """
        return self.fetch_all(query)
    
    def clear_taste_candidates(self) -> None:
        """Clear all existing taste candidates."""
        self.execute("DELETE FROM taste_candidates")
    
    def insert_taste_candidates(self, candidates: list, model_version: str) -> None:
        """
        Insert multiple taste candidates.
        
        Args:
            candidates: List of (tmdb_id, taste_score) tuples
            model_version: Model version identifier
        """
        if not candidates:
            return
        
        # Build batch insert query
        values = []
        params = []
        for tmdb_id, score in candidates:
            values.append("(%s, %s, %s)")
            params.extend([tmdb_id, score, model_version])
        
        query = f"""
            INSERT INTO taste_candidates (tmdb_id, taste_score, model_version)
            VALUES {', '.join(values)}
        """
        
        self.execute(query, tuple(params))
    
    def get_taste_candidates(self, limit: int = 100) -> list:
        """
        Get top taste candidates ordered by score.
        
        Args:
            limit: Maximum number of candidates to return
            
        Returns:
            List of candidate records with movie details
        """
        query = """
            SELECT tc.*, m.title, m.poster_path, m.release_year
            FROM taste_candidates tc
            JOIN movies m ON tc.tmdb_id = m.tmdb_id
            ORDER BY tc.taste_score DESC
            LIMIT %s
        """
        return self.fetch_all(query, (limit,))
    
    # =========================================================================
    # Mood Operations
    # =========================================================================
    
    def upsert_mood(
        self,
        mood_id: str,
        name: str,
        description: str,
        embedding: list[float]
    ) -> None:
        """
        Insert or update a mood with its embedding.
        
        Args:
            mood_id: Unique mood identifier
            name: Display name
            description: Semantic description
            embedding: Embedding vector as list of floats
        """
        query = """
            INSERT INTO moods (id, name, description, embedding)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id)
            DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                embedding = EXCLUDED.embedding
        """
        self.execute(query, (mood_id, name, description, embedding))
    
    def clear_movie_mood_scores(self) -> None:
        """Clear all existing movie mood scores."""
        self.execute("DELETE FROM movie_mood_scores")
    
    def insert_movie_mood_scores(self, scores: list[tuple[int, str, float]]) -> None:
        """
        Insert multiple movie mood scores.
        
        Args:
            scores: List of (tmdb_id, mood_id, similarity_score) tuples
        """
        if not scores:
            return
        
        # Build batch insert query
        values = []
        params = []
        for tmdb_id, mood_id, score in scores:
            values.append("(%s, %s, %s)")
            params.extend([tmdb_id, mood_id, score])
        
        query = f"""
            INSERT INTO movie_mood_scores (tmdb_id, mood_id, similarity_score)
            VALUES {', '.join(values)}
            ON CONFLICT (tmdb_id, mood_id)
            DO UPDATE SET similarity_score = EXCLUDED.similarity_score
        """
        
        self.execute(query, tuple(params))

