from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy import text

from alembic import context

import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.base import Base
from app.models.user import User
from app.models.video import Video
from app.models.event import Event
from app.models.comment import Comment

# Load environment variables
load_dotenv()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the SQLAlchemy URL from environment variable
# Use DATABASE_URL as the primary source, fall back to POSTGRES_URL if available
database_url = os.environ.get("DATABASE_URL", os.environ.get("POSTGRES_URL"))
if database_url:
    # If DATABASE_URL starts with postgres://, convert to postgresql://
    # This is necessary for SQLAlchemy 1.4+ compatibility
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    config.set_main_option("sqlalchemy.url", database_url)
else:
    raise ValueError(
        "No database URL found in environment variables. "
        "Please set either DATABASE_URL or POSTGRES_URL."
    )

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Check if we're starting with an empty database
        tables_exist = False
        try:
            result = connection.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                LIMIT 1
            """))
            tables_exist = bool(result.fetchone())
        except Exception as e:
            print(f"Warning checking for existing tables: {e}")
        
        # If tables already exist but no alembic_version table,
        # we need to stamp the database with a specific version
        # instead of running the initial migrations
        if tables_exist:
            # Check if alembic_version exists
            try:
                result = connection.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'alembic_version'
                    )
                """))
                alembic_exists = result.scalar()
                
                if not alembic_exists:
                    print("Tables exist but no alembic_version table found.")
                    print("Creating alembic_version table and setting version...")
                    
                    # Create alembic_version table and set to the latest revision
                    connection.execute(text("""
                        CREATE TABLE alembic_version (
                            version_num VARCHAR(32) NOT NULL,
                            PRIMARY KEY (version_num)
                        )
                    """))
                    
                    # Skip to the latest migration that matches our current database schema
                    # We're using 'id' as primary keys, not UUIDs
                    connection.execute(text("""
                        INSERT INTO alembic_version (version_num) 
                        VALUES ('971291895341')
                    """))
                    connection.commit()
                    print("Successfully stamped database to correct version (971291895341)")
                    
                    # Return early - we don't need to run any migrations
                    return
            except Exception as e:
                print(f"Warning during alembic_version check: {e}")

        # Run migrations as usual
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            # Handle errors in migrations more gracefully
            compare_type=True,
            compare_server_default=True,
            # Don't include SQLAlchemy's batch mode - this mode is known to cause issues
            render_as_batch=False,
            # Ignore certain columns when autogenerating migrations
            include_schemas=True,
            version_table='alembic_version',
            # Add these options to make migrations more robust
            dialect_opts={"paramstyle": "named"},
            # Enable transaction per migration
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
