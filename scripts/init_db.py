#!/usr/bin/env python3
"""
Database initialization script for Slidex.
Creates the database and runs migrations.
"""

import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from slidex.config import settings
from slidex.logging_config import logger


def create_database_if_not_exists():
    """Create the database if it doesn't exist."""
    # Parse database URL to get connection parameters
    # Format: postgresql://user:password@host:port/dbname
    db_url = settings.database_url
    
    # Extract database name from URL
    db_name = db_url.split("/")[-1].split("?")[0]
    
    # Connect to default postgres database to create our database
    base_url = "/".join(db_url.split("/")[:-1]) + "/postgres"
    
    try:
        conn = psycopg2.connect(base_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        
        if not cur.fetchone():
            logger.info(f"Creating database: {db_name}")
            cur.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(db_name)
            ))
            logger.info(f"Database {db_name} created successfully")
        else:
            logger.info(f"Database {db_name} already exists")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        raise


def run_migrations():
    """Run all migration files in order."""
    migrations_dir = Path(__file__).parent.parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        logger.warning("No migration files found")
        return
    
    try:
        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor()
        
        for migration_file in migration_files:
            logger.info(f"Running migration: {migration_file.name}")
            
            with open(migration_file, "r") as f:
                sql_content = f.read()
            
            cur.execute(sql_content)
            conn.commit()
            
            logger.info(f"Migration {migration_file.name} completed successfully")
        
        cur.close()
        conn.close()
        logger.info("All migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        raise


def main():
    """Main initialization function."""
    logger.info("Starting database initialization")
    
    try:
        create_database_if_not_exists()
        run_migrations()
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
