"""
Script to run a manual SQL migration directly against the database.
This bypasses Alembic to address specific issues.
"""
import os
import sys
import sqlalchemy
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
    
    # Execute manual migrations
    try:
        with engine.connect() as conn:
            # Begin transaction
            with conn.begin():
                # Check database schema
                print("Checking current database schema...")
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """))
                tables = [row[0] for row in result]
                
                if not tables:
                    print("No tables found. Database is empty.")
                    return
                
                print(f"Tables found: {', '.join(tables)}")
                
                # Verify foreign key structure
                if 'comment' in tables and 'event' in tables:
                    print("\nVerifying comment and event relationship...")
                    
                    # Check column names in comment table
                    result = conn.execute(text("""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'comment'
                    """))
                    comment_columns = [row[0] for row in result]
                    print(f"Comment columns: {', '.join(comment_columns)}")
                    
                    # Check if event_id exists in comment table but needs to be of UUID type
                    if 'event_id' in comment_columns:
                        result = conn.execute(text("""
                            SELECT data_type 
                            FROM information_schema.columns 
                            WHERE table_name = 'comment' 
                            AND column_name = 'event_id'
                        """))
                        event_id_type = result.scalar()
                        print(f"event_id type in comment table: {event_id_type}")
                        
                        # Check event table id type
                        result = conn.execute(text("""
                            SELECT data_type 
                            FROM information_schema.columns 
                            WHERE table_name = 'event' 
                            AND column_name = 'id'
                        """))
                        event_id_event_type = result.scalar()
                        print(f"id type in event table: {event_id_event_type}")
                        
                        # Make sure types match
                        if event_id_type != event_id_event_type:
                            print(f"Type mismatch: comment.event_id is {event_id_type} but event.id is {event_id_event_type}")
                            print("Updating event_id type in comment table...")
                            
                            # Drop foreign key constraint if it exists
                            try:
                                conn.execute(text("""
                                    ALTER TABLE comment 
                                    DROP CONSTRAINT IF EXISTS fk_comment_event_id
                                """))
                            except Exception as e:
                                print(f"Warning dropping constraint: {e}")
                            
                            # Update the column type
                            conn.execute(text(f"""
                                ALTER TABLE comment 
                                ALTER COLUMN event_id TYPE {event_id_event_type} USING event_id::{event_id_event_type}
                            """))
                            
                            # Add foreign key constraint
                            conn.execute(text("""
                                ALTER TABLE comment 
                                ADD CONSTRAINT fk_comment_event_id 
                                FOREIGN KEY (event_id) REFERENCES event(id)
                            """))
                            
                            print("Successfully updated event_id column type and constraint")
                
                # Setup alembic version for proper migrations
                if 'alembic_version' not in tables:
                    print("\nSetting up alembic_version table...")
                    conn.execute(text("""
                        CREATE TABLE alembic_version (
                            version_num VARCHAR(32) NOT NULL,
                            PRIMARY KEY (version_num)
                        )
                    """))
                    
                    # Use an appropriate version that doesn't try to create/modify existing tables
                    conn.execute(text("""
                        INSERT INTO alembic_version (version_num) 
                        VALUES ('971291895341')
                    """))
                    print("Successfully created alembic_version table and set version")
                else:
                    # Update version if needed
                    result = conn.execute(text("""
                        SELECT version_num FROM alembic_version
                    """))
                    version = result.scalar()
                    print(f"Current alembic version: {version}")
                    
                    if version in ('add_uuid_columns', 'update_foreign_keys_to_uuid', 'make_uuid_primary_keys'):
                        conn.execute(text("""
                            UPDATE alembic_version
                            SET version_num = '971291895341'
                        """))
                        print("Updated alembic version to 971291895341")
                
            # Commit transaction (automatic with "with conn.begin()")
            print("\nManual migration completed successfully.")
    except Exception as e:
        print(f"Error during manual migration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 