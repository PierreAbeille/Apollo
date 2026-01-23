import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")
password = os.getenv("password")
dbname = os.getenv("dbname") or "postgres"
host = "aws-0-eu-west-1.pooler.supabase.com"

project_ref = "enbpcsovrrckqfcvzyne"
user = f"postgres.{project_ref}"

ports = ["5432", "6543"]

for port in ports:
    print(f"Testing {user} on port {port} ... ", end="", flush=True)
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
        break
    except Exception as e:
        print(f"FAILED: {e}")
