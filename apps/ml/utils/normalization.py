"""Title normalization utilities for matching movies."""
import re
import unicodedata


def normalize_title(title: str) -> str:
    """
    Normalize a movie title for fuzzy matching.
    
    Rules:
    - Convert to lowercase
    - Remove accents/diacritics
    - Remove articles (the, a, an, le, la, les, l')
    - Remove punctuation except spaces
    - Collapse multiple spaces
    - Strip leading/trailing whitespace
    
    Args:
        title: Original movie title
        
    Returns:
        Normalized title string
    """
    if not title:
        return ""
    
    # Lowercase
    title = title.lower()
    
    # Remove accents
    title = unicodedata.normalize('NFKD', title)
    title = ''.join([c for c in title if not unicodedata.combining(c)])
    
    # Remove common articles at the beginning
    # English: the, a, an
    # French: le, la, les, l', un, une
    # Spanish: el, la, los, las, un, una
    articles = r'^(the|a|an|le|la|les|l\'|un|une|el|los|las)\s+'
    title = re.sub(articles, '', title)
    
    # Remove all punctuation except spaces
    title = re.sub(r'[^\w\s]', ' ', title)
    
    # Collapse multiple spaces
    title = re.sub(r'\s+', ' ', title)
    
    # Strip
    return title.strip()


def extract_year(title: str) -> tuple[str, int | None]:
    """
    Extract year from title if present (e.g., "Movie (2023)").
    
    Args:
        title: Movie title possibly containing year
        
    Returns:
        Tuple of (title_without_year, year or None)
    """
    # Match year in parentheses at the end: "Title (2023)"
    match = re.search(r'\((\d{4})\)\s*$', title)
    if match:
        year = int(match.group(1))
        title_clean = title[:match.start()].strip()
        return title_clean, year
    
    return title, None
