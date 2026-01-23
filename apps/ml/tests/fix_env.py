import os
import re
from dotenv import load_dotenv

def fix_env():
    env_path = ".env.local"
    if not os.path.exists(env_path):
        print(f"{env_path} not found.")
        return

    with open(env_path, "r") as f:
        content = f.read()

    db_url_match = re.search(r"DATABASE_URL=['\"]?(postgresql://([^:]+):([^@]+)@([^:/]+):(\d+)/([^? \n'\"]+))", content)
    
    if not db_url_match:
        print("Could not parse DATABASE_URL from .env.local")
        return

    full_url, user, password, host, port, dbname = db_url_match.groups()
    
    # Check if host is the direct one
    if "supabase.co" in host and not "pooler" in host:
        print(f"Detected direct host: {host}")
        # Use pooler host instead
        new_host = "aws-0-eu-west-1.pooler.supabase.com"
        new_port = "6543"
        # Username for pooler must be user.project_ref
        project_ref = "enbpcsovrrckqfcvzyne"
        if project_ref not in user:
            new_user = f"{user}.{project_ref}"
        else:
            new_user = user
            
        print(f"Switching to pooler: {new_host}")
        
        # Add the new variables to .env.local if they don't exist
        new_vars = {
            "user": new_user,
            "password": password,
            "host": new_host,
            "port": new_port,
            "dbname": dbname
        }
        
        updated_content = content
        for k, v in new_vars.items():
            if f"\n{k}=" not in updated_content and not updated_content.startswith(f"{k}="):
                updated_content += f"\n{k}={v}"
        
        # Also update DATABASE_URL to use pooler
        new_url = f"postgresql://{new_user}:{password}@{new_host}:{new_port}/{dbname}?pgbouncer=true"
        # updated_content = updated_content.replace(full_url, new_url) # Let's not overwrite their original URL, just add variables
        
        with open(env_path, "w") as f:
            f.write(updated_content)
        
        print("Updated .env.local with pooler connection details.")

if __name__ == "__main__":
    fix_env()
