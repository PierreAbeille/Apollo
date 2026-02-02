#!/usr/bin/env python3
"""
Pipeline 01: Import Letterboxd + Match TMDB

Reads Letterboxd CSV export, matches movies to TMDB IDs, and populates
the movies and interactions tables.
"""
import csv
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    LETTERBOXD_CSV_PATH,
    ML_DATASET_PATH,
    TMDB_CACHE_DB,
    UNMATCHED_LOG,
    AMBIGUOUS_LOG,
    TMDB_RATE_LIMIT_DELAY,
)
from clients.tmdb import search_movie
from clients.db import DatabaseClient
from utils.normalization import normalize_title, extract_year
from utils.cache import TMDBCache


class LetterboxdImporter:
    """Handles Letterboxd CSV import and TMDB matching."""
    
    def __init__(self, csv_path: str, cache_path: str, use_new_format: bool = False):
        """
        Initialize importer.
        
        Args:
            csv_path: Path to Letterboxd CSV
            cache_path: Path to SQLite cache database
            use_new_format: If True, use new ml_dataset_full.csv format
        """
        self.csv_path = csv_path
        self.cache = TMDBCache(cache_path)
        self.db = DatabaseClient()
        self.use_new_format = use_new_format
        
        # Statistics
        self.stats = {
            "total": 0,
            "matched": 0,
            "cached": 0,
            "unmatched": 0,
            "ambiguous": 0,
            "api_calls": 0,
        }
        
        # Tracking for logs
        self.unmatched_movies = []
        self.ambiguous_movies = []
    
    def match_movie(self, title: str, year: Optional[int]) -> Optional[Tuple[int, dict]]:
        """
        Match a movie to TMDB ID, using cache when possible.
        
        Args:
            title: Movie title
            year: Release year (optional)
            
        Returns:
            Tuple of (tmdb_id, movie_data) or None if no match
        """
        title_norm = normalize_title(title)
        
        # Check cache first
        cached_id = self.cache.get(title_norm, year)
        if cached_id:
            self.stats["cached"] += 1
            print(f"  ✓ Cache hit: {title} → {cached_id}")
            
            # We don't have full movie data from cache, but we have the ID
            # The database upsert will handle getting data from TMDB if needed
            return cached_id, {"title": title, "release_year": year}
        
        # Search TMDB
        print(f"  🔍 Searching TMDB: {title} ({year or 'unknown year'})")
        time.sleep(TMDB_RATE_LIMIT_DELAY)  # Rate limiting
        
        try:
            results = search_movie(title, language="fr-FR")
            self.stats["api_calls"] += 1
            
            if not results.get("results"):
                print(f"  ✗ No results found")
                self.stats["unmatched"] += 1
                self.unmatched_movies.append({"title": title, "year": year})
                return None
            
            # Filter by year if provided
            candidates = results["results"]
            if year:
                # Allow ±1 year tolerance
                candidates = [
                    m for m in candidates
                    if m.get("release_date") and 
                    abs(int(m["release_date"][:4]) - year) <= 1
                ]
            
            if not candidates:
                print(f"  ✗ No year match")
                self.stats["unmatched"] += 1
                self.unmatched_movies.append({"title": title, "year": year})
                return None
            
            # Check if ambiguous (multiple strong matches)
            if len(candidates) > 1:
                # If top result has significantly higher popularity, use it
                top = candidates[0]
                second = candidates[1]
                if top.get("popularity", 0) < second.get("popularity", 0) * 1.5:
                    print(f"  ⚠ Ambiguous match: {len(candidates)} candidates")
                    self.stats["ambiguous"] += 1
                    self.ambiguous_movies.append({
                        "title": title,
                        "year": year,
                        "candidates": [
                            f"{m['title']} ({m.get('release_date', 'N/A')[:4]}) [ID:{m['id']}]"
                            for m in candidates[:3]
                        ]
                    })
            
            # Use top result
            movie = candidates[0]
            tmdb_id = movie["id"]
            
            # Cache the match
            self.cache.set(title_norm, year, tmdb_id, confidence="exact" if year else "fuzzy")
            
            print(f"  ✓ Matched: {movie['title']} ({movie.get('release_date', 'N/A')[:4]}) [ID:{tmdb_id}]")
            self.stats["matched"] += 1
            
            # Prepare movie data
            movie_data = {
                "title": movie["title"],
                "release_year": int(movie["release_date"][:4]) if movie.get("release_date") else None,
                "poster_path": movie.get("poster_path"),
            }
            
            return tmdb_id, movie_data
            
        except Exception as e:
            print(f"  ✗ Error searching TMDB: {e}")
            self.stats["unmatched"] += 1
            self.unmatched_movies.append({"title": title, "year": year, "error": str(e)})
            return None
    
    def process_row(self, row: dict) -> bool:
        """
        Process a single CSV row.
        
        Args:
            row: CSV row as dictionary
            
        Returns:
            True if successfully processed
        """
        title = row.get("title", "").strip()
        if not title:
            return False
        
        # Parse year - handle both old and new format
        if self.use_new_format:
            # New format: 'year' column directly
            year_str = row.get("year", "").strip()
            year = int(year_str) if year_str.isdigit() else None
            
            # Parse interaction type to derive is_done and is_wishlisted
            interaction_type = row.get("interaction", "").strip().lower()
            is_done = interaction_type == "watched"
            is_wishlisted = interaction_type == "watchlist"
            
            # Rating in new format is 1-5 (Letterboxd scale), convert to 1-10
            rating_str = row.get("rating", "").strip()
            if rating_str:
                try:
                    letterboxd_rating = float(rating_str)
                    rating = letterboxd_rating * 2  # Convert 1-5 to 2-10 scale
                except ValueError:
                    rating = None
            else:
                rating = None
        else:
            # Old format: 'release_date' column
            release_date = row.get("release_date", "").strip()
            year = int(release_date) if release_date.isdigit() else None
            
            # Old format flags
            is_done = True  # Assumed watched in old format
            is_wishlisted = row.get("is_wishlisted", "").lower() == "true"
            
            # Rating already in 1-10 scale
            rating_str = row.get("rating", "").strip()
            rating = float(rating_str) if rating_str else None
        
        is_recommended = row.get("is_recommended", "").lower() == "true"
        
        # Match to TMDB
        match_result = self.match_movie(title, year)
        if not match_result:
            return False
        
        tmdb_id, movie_data = match_result
        
        # Upsert to database
        try:
            self.db.upsert_movie(
                tmdb_id=tmdb_id,
                title=movie_data["title"],
                release_year=movie_data.get("release_year"),
                poster_path=movie_data.get("poster_path"),
            )
            
            self.db.upsert_interaction(
                tmdb_id=tmdb_id,
                rating=rating,
                is_done=is_done,
                is_wishlisted=is_wishlisted,
                is_recommended=is_recommended,
                source="letterboxd",
            )
            
            return True
            
        except Exception as e:
            print(f"  ✗ Database error: {e}")
            return False
    
    def write_logs(self):
        """Write unmatched and ambiguous movies to CSV logs."""
        # Unmatched log
        if self.unmatched_movies:
            with open(UNMATCHED_LOG, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["title", "year", "error"])
                writer.writeheader()
                for movie in self.unmatched_movies:
                    writer.writerow({
                        "title": movie.get("title"),
                        "year": movie.get("year", ""),
                        "error": movie.get("error", ""),
                    })
            print(f"\n📝 Unmatched movies logged to: {UNMATCHED_LOG}")
        
        # Ambiguous log
        if self.ambiguous_movies:
            with open(AMBIGUOUS_LOG, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["title", "year", "candidates"])
                writer.writeheader()
                for movie in self.ambiguous_movies:
                    writer.writerow({
                        "title": movie.get("title"),
                        "year": movie.get("year", ""),
                        "candidates": " | ".join(movie.get("candidates", [])),
                    })
            print(f"📝 Ambiguous matches logged to: {AMBIGUOUS_LOG}")
    
    def run(self):
        """Main import process."""
        print("=" * 60)
        print("Pipeline 01: Import Letterboxd + Match TMDB")
        print("=" * 60)
        print(f"\nReading: {self.csv_path}")
        
        # Check if CSV exists
        if not Path(self.csv_path).exists():
            print(f"✗ Error: CSV file not found: {self.csv_path}")
            return
        
        # Connect to database
        self.db.connect()
        
        # Read and process CSV
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.stats["total"] += 1
                print(f"\n[{self.stats['total']}] Processing: {row.get('title')}")
                self.process_row(row)
        
        # Close database
        self.db.close()
        
        # Write logs
        self.write_logs()
        
        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total movies:      {self.stats['total']}")
        print(f"✓ Matched:         {self.stats['matched']}")
        print(f"  - From cache:    {self.stats['cached']}")
        print(f"  - From API:      {self.stats['matched'] - self.stats['cached']}")
        print(f"✗ Unmatched:       {self.stats['unmatched']}")
        print(f"⚠ Ambiguous:       {self.stats['ambiguous']}")
        print(f"📡 TMDB API calls: {self.stats['api_calls']}")
        print("\nCache stats:", self.cache.stats())
        print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Import Letterboxd data")
    parser.add_argument("--new-format", action="store_true", 
                        help="Use new ml_dataset_full.csv format")
    parser.add_argument("--csv", type=str, default=None,
                        help="Path to CSV file (defaults based on format)")
    args = parser.parse_args()
    
    # Determine CSV path
    if args.csv:
        csv_path = args.csv
    elif args.new_format:
        csv_path = ML_DATASET_PATH
    else:
        csv_path = LETTERBOXD_CSV_PATH
    
    print(f"Using CSV: {csv_path}")
    print(f"Format: {'NEW (ml_dataset_full.csv)' if args.new_format else 'OLD (letterboxd-data.csv)'}")
    
    importer = LetterboxdImporter(csv_path, TMDB_CACHE_DB, use_new_format=args.new_format)
    importer.run()
