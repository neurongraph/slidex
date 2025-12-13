#!/usr/bin/env python3
"""
Grant database permissions to allow external tools to access the database.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from slidex.config import settings
from slidex.logging_config import logger
import psycopg2


def grant_permissions():
    """Grant permissions on all tables and sequences."""
    
    logger.info("Granting database permissions...")
    
    try:
        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Grant on existing tables
        logger.info("Granting permissions on existing tables...")
        cur.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO PUBLIC")
        
        # Grant on sequences
        logger.info("Granting permissions on sequences...")
        cur.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO PUBLIC")
        
        # Grant on future tables
        logger.info("Setting default privileges for future tables...")
        cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO PUBLIC")
        cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO PUBLIC")
        
        cur.close()
        conn.close()
        
        logger.info("✓ Permissions granted successfully")
        print("\n✓ Database permissions granted successfully!")
        print("You should now be able to access tables from DBeaver.")
        
    except Exception as e:
        logger.error(f"Error granting permissions: {e}")
        print(f"\n✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Make sure the slidex database exists")
        print("3. You may need superuser privileges to grant permissions")
        sys.exit(1)


if __name__ == "__main__":
    grant_permissions()
