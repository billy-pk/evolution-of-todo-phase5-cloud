import os
import sys
import psycopg2

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


def run_jwks_migration():
    """
    Execute JWKS table migration for Better Auth JWT plugin.
    """
    # Connect to the database
    conn = psycopg2.connect(
        settings.DATABASE_URL
    )
    cursor = conn.cursor()

    # Read the migration file
    migration_file_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "migrations",
        "003_create_jwks_table.sql"
    )

    with open(migration_file_path, 'r') as migration_file:
        migration_sql = migration_file.read()

    # Execute the migration
    try:
        cursor.execute(migration_sql)
        conn.commit()
        print("JWKS table migration completed successfully!")
        print("Created table: jwks")
    except Exception as e:
        print(f"Error during JWKS migration: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_jwks_migration()
