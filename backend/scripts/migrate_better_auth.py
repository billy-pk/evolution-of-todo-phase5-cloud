import os
import sys
import psycopg2

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


def run_better_auth_migration():
    """
    Execute Better Auth database migration to create user, session, account, and verification tables.
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
        "002_create_better_auth_tables.sql"
    )

    with open(migration_file_path, 'r') as migration_file:
        migration_sql = migration_file.read()

    # Execute the migration
    try:
        cursor.execute(migration_sql)
        conn.commit()
        print("Better Auth migration completed successfully!")
        print("Created tables: user, session, account, verification")
    except Exception as e:
        print(f"Error during Better Auth migration: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_better_auth_migration()
