"""
Database initialization script to create all tables in the database.
Run this directly against your Render database to set up the schema.
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import importlib.util
import pathlib

# Load environment variables
load_dotenv()

# Add parent directory to path so we can import from app
current_dir = pathlib.Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

def main():
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
    
    # Import the Base model with all models attached
    try:
        from app.models.base import Base
        from app.models.user import User
        from app.models.video import Video
        from app.models.event import Event
        from app.models.comment import Comment
        
        print("Imported models successfully.")
    except ImportError as e:
        print(f"Error importing models: {str(e)}")
        sys.exit(1)
    
    # Create all tables
    try:
        # First check if tables already exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """))
            existing_tables = [row[0] for row in result]
            
        if existing_tables:
            print(f"Found existing tables: {', '.join(existing_tables)}")
            
            # If tables exist but no alembic_version, create it
            if 'alembic_version' not in existing_tables:
                with engine.connect() as conn:
                    with conn.begin():
                        print("Creating alembic_version table...")
                        conn.execute(text("""
                            CREATE TABLE alembic_version (
                                version_num VARCHAR(32) NOT NULL,
                                PRIMARY KEY (version_num)
                            )
                        """))
                        
                        # Set to version that matches our current schema
                        conn.execute(text("""
                            INSERT INTO alembic_version (version_num) 
                            VALUES ('971291895341')
                        """))
                        print("Successfully created alembic_version table and set version")
        else:
            # Create all tables from models
            print("Creating all tables from models...")
            Base.metadata.create_all(engine)
            
            # Create alembic_version table
            with engine.connect() as conn:
                with conn.begin():
                    print("Creating alembic_version table...")
                    conn.execute(text("""
                        CREATE TABLE alembic_version (
                            version_num VARCHAR(32) NOT NULL,
                            PRIMARY KEY (version_num)
                        )
                    """))
                    
                    # Set to version that matches our current schema
                    conn.execute(text("""
                        INSERT INTO alembic_version (version_num) 
                        VALUES ('971291895341')
                    """))
            
            print("Successfully created all tables!")
        
        # Check which tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            print(f"Tables in database: {', '.join(tables)}")
            
    except Exception as e:
        print(f"Error creating tables: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 