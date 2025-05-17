from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Database configuration
# Check for DATABASE_URL first (Render's default), then fall back to POSTGRES_URL
database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")

if database_url is None:
    raise ValueError("No database URL found in environment variables. Please set either DATABASE_URL or POSTGRES_URL.")

# Convert postgres:// to postgresql:// if necessary (for SQLAlchemy 1.4+ compatibility)
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 