import os
import psycopg2
from dotenv import load_dotenv

# Load .env.local if it exists
if os.path.exists(".env.local"):
    load_dotenv(".env.local")
else:
    load_dotenv()

def get_connection():
    """
    Establishes a connection to the PostgreSQL database using environment variables.
    Handles multiple variable naming conventions and focuses on IPv4 compatibility.
    """
    
    # 1. Try DATABASE_URL (Best for Poolers)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            return psycopg2.connect(db_url)
        except Exception as e:
            if "pooler" in db_url:
                print(f"Pooler connection failed: {e}")
            else:
                print(f"Direct connection failed (likely IPv4/IPv6 issue): {e}")

    # 2. Fallback to individual components
    # We try both standard Supabase and common Python naming conventions
    user = os.getenv("user") or os.getenv("DB_USER") or os.getenv("POSTGRES_USER")
    password = os.getenv("password") or os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("host") or os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST")
    port = os.getenv("port") or os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or "5432"
    dbname = os.getenv("dbname") or os.getenv("DB_NAME") or os.getenv("POSTGRES_DB") or "postgres"

    if all([user, password, host]):
        try:
            return psycopg2.connect(
                user=user,
                password=password,
                host=host,
                port=port,
                dbname=dbname
            )
        except Exception as e:
            print(f"Connection with individual variables failed: {e}")
    
    return None

if __name__ == "__main__":
    conn = get_connection()
    if conn:
        print("Successfully connected!")
        conn.close()
    else:
        print("Could not establish connection. Please check your .env.local file.")
