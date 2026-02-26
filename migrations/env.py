from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import sys
import os

# Import your models and Base
from App.database.connection import Base 
from App.models.model import User, Company, Document, DocumentChunk 
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Setup sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set target metadata
target_metadata = Base.metadata

# Alembic Config object
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Use environment variable if available, else fallback to alembic.ini
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Create a custom config section to inject our dynamic URL
    alembic_config = config.get_section(config.config_ini_section, {})
    
    # DYNAMIC URL INJECTION: This overrides localhost with db:5432
    alembic_config["sqlalchemy.url"] = os.getenv("DATABASE_URL")

    connectable = engine_from_config(
        alembic_config,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
