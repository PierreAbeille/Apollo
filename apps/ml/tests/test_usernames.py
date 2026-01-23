import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
password = os.getenv("password")
dbname = os.getenv("dbname") or "postgres"
host = "aws-0-eu-west-1.pooler.supabase.com"
port = "5432"

# Project ref extracted from your hostname
project_ref = "enbpcsovrrckqfcvzyne"

# Try different username formats
usernames = [
    f"postgres.{project_ref}",
    f"{project_ref}.postgres",
    "postgres"
]

for user in usernames:
    print(f"Testing username: {user} ... ", end="", flush=True)
    try:
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            dbname=dbname,
            connect_timeout=5
        )
        print("SUCCESS!")
        conn.close()
        # If success, update .env.local
        print(f"\nUPDATING .env.local with working user: {user}")
        with open(".env.local", "r") as f:
            lines = f.readlines()
        
        with open(".env.local", "w") as f:
            for line in lines:
                if line.startswith("user="):
                    f.write(f"user={user}\n")
                elif line.startswith("host="):
                    f.write(f"host={host}\n")
                elif line.startswith("port="):
                    f.write(f"port={port}\n")
                else:
                    f.write(line)
        break
    except Exception as e:
        print(f"FAILED: {e}")
