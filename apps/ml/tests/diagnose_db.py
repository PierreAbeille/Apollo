import os
import psycopg2
import socket
from dotenv import load_dotenv

load_dotenv(".env.local")
db_url = os.getenv("DATABASE_URL")

print(f"Checking DATABASE_URL...")
host = "db.enbpcsovrrckqfcvzyne.supabase.co"

try:
    print(f"Attempting to resolve {host}...")
    addr_info = socket.getaddrinfo(host, 5432)
    print(f"Resolved to: {addr_info}")
except Exception as e:
    print(f"DNS Resolution failed for {host}: {e}")
    print("\n--- DIAGNOSIS ---")
    print("Your environment seems unable to resolve the IPv6-only Supabase direct host.")
    print("Supabase now uses IPv6-only for direct connections in some regions.")
    print("Solution: Use the Supabase Connection Pooler (Port 6543) which supports IPv4.")
    
    pooler_host = "aws-0-eu-west-1.pooler.supabase.com"
    try:
        print(f"\nChecking Pooler host {pooler_host}...")
        pooler_addr = socket.getaddrinfo(pooler_host, 6543)
        print(f"Pooler resolved to: {pooler_addr[0][4][0]} (IPv4 supported!)")
    except:
        print("Pooler host also unreachable.")

print("\n--- SUGGESTED FIX ---")
print("1. Go to your Supabase Dashboard -> Project Settings -> Database")
print("2. Copy the 'Connection String' for 'Transaction Pooler'")
print("3. Update your DATABASE_URL in .env.local with this string.")
