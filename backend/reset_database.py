#!/usr/bin/env python3
"""Script to delete and recreate the database"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def get_db_params():
    """Parse database URL and return connection parameters"""
    db_url = settings.DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    parts = db_url.replace("postgresql://", "").split("@")
    if len(parts) != 2:
        raise ValueError(f"Invalid database URL format: {db_url}")
    
    auth_part, host_part = parts
    user, password = auth_part.split(":")
    host, port_and_db = host_part.split(":")
    port, database = port_and_db.split("/")
    
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database
    }

def delete_database():
    """Delete the database only"""
    print(f"\n🗑️  DELETING DATABASE\n")
    print("=" * 80)
    
    params = get_db_params()
    print(f"Database: {params['host']}:{params['port']}/{params['database']}")
    print(f"User: {params['user']}\n")
    
    try:
        # Connect to PostgreSQL server (connect to postgres database)
        admin_conn = psycopg2.connect(
            host=params['host'],
            port=params['port'],
            user=params['user'],
            password=params['password'],
            database="postgres"  # Connect to default postgres database
        )
        admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        admin_cursor = admin_conn.cursor()
        
        # Terminate all connections to the database first
        print(f"🔌 Terminating connections to '{params['database']}'...")
        admin_cursor.execute(
            f"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '{params['database']}' AND pid <> pg_backend_pid();"
        )
        print(f"   ✅ Connections terminated")
        
        # Drop existing database if it exists
        print(f"\n🗑️  Dropping database '{params['database']}' if it exists...")
        admin_cursor.execute(f"DROP DATABASE IF EXISTS {params['database']};")
        print(f"   ✅ Dropped database '{params['database']}'")
        
        admin_cursor.close()
        admin_conn.close()
        
        print(f"\n✅ Database deletion complete!")
        print(f"   Database '{params['database']}' has been deleted\n")
        
    except Exception as e:
        print(f"\n❌ Error deleting database: {e}")
        import traceback
        traceback.print_exc()

def create_database():
    """Create the database and initialize tables"""
    print(f"\n✨ CREATING DATABASE\n")
    print("=" * 80)
    
    params = get_db_params()
    print(f"Database: {params['host']}:{params['port']}/{params['database']}")
    print(f"User: {params['user']}\n")
    
    try:
        # Connect to PostgreSQL server (connect to postgres database)
        admin_conn = psycopg2.connect(
            host=params['host'],
            port=params['port'],
            user=params['user'],
            password=params['password'],
            database="postgres"  # Connect to default postgres database
        )
        admin_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        admin_cursor = admin_conn.cursor()
        
        # Create new database
        print(f"✨ Creating new database '{params['database']}'...")
        admin_cursor.execute(f"CREATE DATABASE {params['database']};")
        print(f"   ✅ Created database '{params['database']}'")
        
        admin_cursor.close()
        admin_conn.close()
        
        # Now initialize the tables in the new database
        print(f"\n📋 Initializing tables...")
        from app.database import init_db
        init_db()
        print(f"   ✅ Tables initialized")
        
        print(f"\n✅ Database creation complete!")
        print(f"   Database: {params['database']}")
        print(f"   Tables: scraped_items")
        print(f"   Status: Ready for use\n")
        
    except Exception as e:
        print(f"\n❌ Error creating database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        if action == "delete":
            delete_database()
        elif action == "create":
            create_database()
        else:
            print(f"\n❌ Unknown action: {action}")
            print(f"Usage: python reset_database.py [delete|create]\n")
    else:
        # Default: delete first
        print(f"\n⚠️  No action specified. Running DELETE only.")
        print(f"   To create: python reset_database.py create\n")
        delete_database()
