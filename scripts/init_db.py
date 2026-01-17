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
    """
    Run database initialization.
    Prefers consolidated init_schema.sql if available, otherwise runs individual migrations.
    """
    migrations_dir = Path(__file__).parent.parent / "migrations"
    consolidated_schema = migrations_dir / "init_schema.sql"
    
    try:
        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor()
        
        # Prefer consolidated schema if it exists
        if consolidated_schema.exists():
            logger.info("Using consolidated schema: init_schema.sql")
            with open(consolidated_schema, "r") as f:
                sql_content = f.read()
            
            cur.execute(sql_content)
            conn.commit()
            logger.info("Consolidated schema applied successfully")
        else:
            # Fall back to individual migration files
            migration_files = sorted([
                f for f in migrations_dir.glob("*.sql")
                if f.name.startswith(("001_", "002_", "003_"))
            ])
            
            if not migration_files:
                logger.warning("No migration files found")
                return
            
            logger.info("Using individual migration files")
            for migration_file in migration_files:
                logger.info(f"Running migration: {migration_file.name}")
                
                with open(migration_file, "r") as f:
                    sql_content = f.read()
                
                cur.execute(sql_content)
                conn.commit()
                
                logger.info(f"Migration {migration_file.name} completed successfully")
        
        cur.close()
        conn.close()
        logger.info("Database initialization completed successfully")
        
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
