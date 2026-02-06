#!/usr/bin/env python3
"""
Pipeline 06: Import Reviews

Reads Letterboxd reviews CSV and populates the review_text column in interactions.
"""
import csv
import sys
import time
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import LETTERBOXD_CSV_PATH, TMDB_CACHE_DB, TMDB_RATE_LIMIT_DELAY
from clients.tmdb import search_movie
from clients.db import DatabaseClient
from utils.normalization import normalize_title, extract_year
from utils.cache import TMDBCache

class ReviewImporter:
    def __init__(self, review_csv_path: str, cache_path: str):
        self.csv_path = review_csv_path
        self.cache = TMDBCache(cache_path)
        self.db = DatabaseClient()
        self.stats = {"total": 0, "updated": 0, "skipped": 0, "errors": 0}

    def run(self):
        print("=" * 60)
        print("Pipeline 06: Import Reviews")
        print("=" * 60)

        if not Path(self.csv_path).exists():
            print(f"✗ Error: CSV file not found: {self.csv_path}")
            return

        self.db.connect()
        
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.stats["total"] += 1
                title = row.get("Name", "").strip()
                year = int(row.get("Year")) if row.get("Year") and row.get("Year").isdigit() else None
                review_text = row.get("Review", "").strip()
                
                if not review_text:
                    self.stats["skipped"] += 1
                    continue

                if self.stats["total"] % 50 == 0:
                    print(f"[{self.stats['total']}] Processing: {title}")

                # Match movie using cache first (assume specific movies are already imported in step 01)
                tmdb_id = self.cache.get(normalize_title(title), year)
                
                if not tmdb_id:
                    # Try to find without cache if missing (unlikely if step 01 ran, but possible)
                    # For safety, we only rely on cache to ensure we match the *same* movie
                    # or simple TMDB search if absolutely necessary.
                    print(f"  ⚠ Not found in cache: {title} ({year})")
                    self.stats["skipped"] += 1
                    continue

                try:
                    # Update interaction
                    query = """
                        UPDATE interactions 
                        SET review_text = %s, updated_at = NOW()
                        WHERE tmdb_id = %s
                    """
                    # We only update if the record exists (it should from step 01)
                    cursor = self.db.conn.cursor()
                    cursor.execute(query, (review_text, tmdb_id))
                    count = cursor.rowcount
                    self.db.conn.commit()
                    cursor.close()

                    if count > 0:
                        self.stats["updated"] += 1
                    else:
                        # Interaction might be missing if 01 didnt import it (e.g. ignored)
                        self.stats["skipped"] += 1
                        
                except Exception as e:
                    self.db.conn.rollback() # Reset transaction on error
                    print(f"  ✗ DB Error: {e}")
                    self.stats["errors"] += 1

        self.db.close()
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Total rows:        {self.stats['total']}")
        print(f"✓ Reviews Updated: {self.stats['updated']}")
        print(f"✗ Skipped:         {self.stats['skipped']}")
        print(f"⚠ Errors:          {self.stats['errors']}")
        print("=" * 60)

if __name__ == "__main__":
    # Letterboxd export usually has reviews.csv in the same folder
    # We'll assume the same base path logic or passed arg
    # Since LETTERBOXD_CSV_PATH points to ratings.csv or just the folder? 
    # Usually LETTERBOXD_CSV_PATH is the ratings file. 
    # We can deduce the directory.
    
    # Actually, relying on the hardcoded path from finding earlier:
    # _dev/LBD_to_SC/letterboxd-_hellopedro-2026-01-02-15-49-utc/reviews.csv
    
    default_csv = "/Users/_hellopedro/_dev/LBD_to_SC/letterboxd-_hellopedro-2026-01-02-15-49-utc/reviews.csv"
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=str, default=default_csv, help="Path to reviews.csv")
    args = parser.parse_args()

    importer = ReviewImporter(args.csv, TMDB_CACHE_DB)
    importer.run()
