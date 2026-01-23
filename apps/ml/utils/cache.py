"""SQLite cache for TMDB title-to-ID matching."""
import sqlite3
from typing import Optional


class TMDBCache:
    """Persistent cache for TMDB movie ID lookups."""
    
    def __init__(self, db_path: str):
        """
        Initialize cache with SQLite database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create cache table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tmdb_match_cache (
                title_norm TEXT NOT NULL,
                year INTEGER,
                tmdb_id INTEGER NOT NULL,
                confidence TEXT NOT NULL,  -- 'exact', 'fuzzy', 'manual'
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (title_norm, year)
            )
        """)
        # Index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_title_year 
            ON tmdb_match_cache(title_norm, year)
        """)
        conn.commit()
        conn.close()
    
    def get(self, title_norm: str, year: Optional[int] = None) -> Optional[int]:
        """
        Retrieve cached TMDB ID.
        
        Args:
            title_norm: Normalized movie title
            year: Release year (optional)
            
        Returns:
            TMDB ID if cached, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if year:
            cursor.execute(
                "SELECT tmdb_id FROM tmdb_match_cache WHERE title_norm = ? AND year = ?",
                (title_norm, year)
            )
        else:
            # Try without year if not provided
            cursor.execute(
                "SELECT tmdb_id FROM tmdb_match_cache WHERE title_norm = ? AND year IS NULL",
                (title_norm,)
            )
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def set(self, title_norm: str, year: Optional[int], tmdb_id: int, confidence: str = "exact"):
        """
        Cache a TMDB ID lookup.
        
        Args:
            title_norm: Normalized movie title
            year: Release year (optional)
            tmdb_id: TMDB movie ID
            confidence: Match confidence level ('exact', 'fuzzy', 'manual')
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO tmdb_match_cache (title_norm, year, tmdb_id, confidence)
            VALUES (?, ?, ?, ?)
        """, (title_norm, year, tmdb_id, confidence))
        
        conn.commit()
        conn.close()
    
    def clear(self):
        """Clear the entire cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tmdb_match_cache")
        conn.commit()
        conn.close()
    
    def stats(self) -> dict:
        """Get cache statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM tmdb_match_cache")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT confidence, COUNT(*) FROM tmdb_match_cache GROUP BY confidence")
        by_confidence = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_entries": total,
            "by_confidence": by_confidence
        }
