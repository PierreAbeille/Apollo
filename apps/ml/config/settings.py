"""Configuration settings for ML pipelines."""
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
EMBEDDINGS_DIR = os.path.join(DATA_DIR, "embeddings")

# Ensure directories exist
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

# Database
DB_BATCH_SIZE = 100

# TMDB
TMDB_RATE_LIMIT_DELAY = 1.2  # seconds between API calls (limit 50/min)
TMDB_MAX_RETRIES = 3
TMDB_TIMEOUT = 10  # seconds

# Embeddings
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_BATCH_SIZE = 32

# Recommendations
MIN_RATING_FOR_SIMILAR = 8  # Fetch similar movies for ratings >= this
SIMILAR_MOVIES_PER_FILM = 20  # How many similar movies to fetch per high-rated film
MAX_TASTE_CANDIDATES = 2000  # Top N candidates to store
NEW_CANDIDATE_BATCH_SIZE = 50  # Process new candidates in batches to manage memory

# Letterboxd
LETTERBOXD_CSV_PATH = os.path.join(RAW_DATA_DIR, "letterboxd", "letterboxd-data.csv")
ML_DATASET_PATH = os.path.join(RAW_DATA_DIR, "letterboxd", "ml_dataset_full.csv")

# Cache
TMDB_CACHE_DB = os.path.join(CACHE_DIR, "tmdb_match.db")

# Logs
UNMATCHED_LOG = os.path.join(LOGS_DIR, "unmatched.csv")
AMBIGUOUS_LOG = os.path.join(LOGS_DIR, "ambiguous.csv")

# Training data output
TRAIN_DATA_DIR = os.path.join(DATA_DIR, "train")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Ensure new directories exist
os.makedirs(TRAIN_DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# XGBoost settings
XGBOOST_SEED = 42
XGBOOST_TEST_SIZE = 0.2
XGBOOST_N_ESTIMATORS = 100
XGBOOST_MAX_DEPTH = 6
XGBOOST_LEARNING_RATE = 0.1

# Feature engineering settings
TOP_GENRES = 20
TOP_KEYWORDS = 300
TOP_LANGUAGES = 10
TOP_COUNTRIES = 20

# Labeling thresholds
POSITIVE_RATING_THRESHOLD = 9  # rating >= 9 -> y=1
NEGATIVE_RATING_THRESHOLD = 5  # rating <= 5 -> y=0

# V1.5: Anti-centroid (negative profile)
ANTI_CENTROID_THRESHOLD = 4  # rating <= 4 -> used for anti-centroid

# V1.5: MMR Reranking
MMR_ENABLED = True
MMR_LAMBDA = 0.7  # 0.0 = full diversity, 1.0 = no diversity (only relevance)
MMR_TOP_K = 200   # Apply MMR to top K candidates before final selection

