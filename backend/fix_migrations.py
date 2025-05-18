"""
Script to fix the Alembic migration history to match our actual database schema.
This avoids any issues with conflicting migrations.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    
    if not database_url:
        print("Error: No database URL found in environment variables.")
        print("Please set either DATABASE_URL or POSTGRES_URL.")
        sys.exit(1)
    
    # Convert postgres:// to postgresql:// if necessary
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    print(f"Connecting to database: {database_url[:database_url.index('@')]}")
    
    # Create engine
    engine = create_engine(database_url)
    
    # Get list of all migrations in alembic/versions directory
    import glob
    import pathlib
    
    versions_dir = pathlib.Path(__file__).parent / "alembic" / "versions"
    migration_files = glob.glob(str(versions_dir / "*.py"))
    migrations = []
    
    # Parse each migration file to find the most recent one
    import re
    
    latest_migration = None
    for file_path in migration_files:
        with open(file_path, 'r') as f:
            content = f.read()
            # Look for revision ID
            revision_match = re.search(r"revision\s*=\s*['\"]([^'\"]+)['\"]", content)
            if revision_match:
                revision = revision_match.group(1)
                # Look for down_revision
                down_match = re.search(r"down_revision\s*=\s*['\"]?([^'\"]+)['\"]?", content)
                down_revision = down_match.group(1) if down_match else None
                
                migrations.append((revision, down_revision, file_path))
    
    # Find the latest revision (with no other revisions pointing to it)
    all_revisions = {m[0] for m in migrations}
    all_down_revisions = {m[1] for m in migrations if m[1]}
    
    latest_revisions = all_revisions - all_down_revisions
    
    if not latest_revisions:
        print("Error: Could not determine latest migration.")
        sys.exit(1)
    
    if len(latest_revisions) > 1:
        print(f"Warning: Found multiple latest revisions: {latest_revisions}")
        print("Using the first one as the target.")
    
    target_revision = list(latest_revisions)[0]
    print(f"Latest migration ID: {target_revision}")
    
    # Update the database
    try:
        with engine.connect() as conn:
            with conn.begin():
                # Check if alembic_version exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'alembic_version'
                    )
                """))
                alembic_exists = result.scalar()
                
                if not alembic_exists:
                    print("Creating alembic_version table...")
                    conn.execute(text("""
                        CREATE TABLE alembic_version (
                            version_num VARCHAR(32) NOT NULL,
                            PRIMARY KEY (version_num)
                        )
                    """))
                    conn.execute(text(f"""
                        INSERT INTO alembic_version (version_num)
                        VALUES ('{target_revision}')
                    """))
                    print(f"Set alembic version to {target_revision}")
                else:
                    print("Updating alembic_version table...")
                    conn.execute(text(f"""
                        UPDATE alembic_version
                        SET version_num = '{target_revision}'
                    """))
                    print(f"Updated alembic version to {target_revision}")
                
            print("Migration history fixed successfully.")
    except Exception as e:
        print(f"Error fixing migration history: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 