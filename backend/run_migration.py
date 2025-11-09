"""
Run the document_summaries table migration
"""
import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path if env_path.exists() else None)

def run_migration():
    """Run the document_summaries table migration."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5433")),
            database=os.getenv("POSTGRES_DB", "lola_db"),
            user=os.getenv("POSTGRES_USER", "lola"),
            password=os.getenv("POSTGRES_PASSWORD", "lola_dev_password"),
        )
        
        # Read the migration file
        migration_path = Path(__file__).parent.parent / "app" / "supabase" / "migrations" / "create-document-summaries-table.sql"
        
        if not migration_path.exists():
            print(f"Error: Migration file not found at {migration_path}")
            sys.exit(1)
        
        with open(migration_path, "r", encoding="utf-8") as f:
            migration_sql = f.read()
        
        print("Running migration: create-document-summaries-table.sql")
        
        with conn.cursor() as cur:
            cur.execute(migration_sql)
            conn.commit()
        
        print("Migration applied successfully!")
        conn.close()
        
    except Exception as e:
        print(f"Error running migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()

