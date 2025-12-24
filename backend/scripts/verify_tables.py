import os
import sys
import psycopg2

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings


def verify_tables():
    """
    Verify all required tables exist in the database.
    """
    conn = psycopg2.connect(settings.DATABASE_URL)
    cursor = conn.cursor()

    try:
        # Query to get all tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cursor.fetchall()

        print("Tables in database:")
        print("-" * 40)
        for table in tables:
            print(f"  ✓ {table[0]}")

        print("-" * 40)
        print(f"Total tables: {len(tables)}")

        # Check for required tables
        required_tables = ['user', 'session', 'account', 'verification', 'tasks']
        table_names = [t[0] for t in tables]

        print("\nRequired tables check:")
        print("-" * 40)
        all_present = True
        for req_table in required_tables:
            if req_table in table_names:
                print(f"  ✓ {req_table}")
            else:
                print(f"  ✗ {req_table} (MISSING)")
                all_present = False

        if all_present:
            print("\n✓ All required tables are present!")
        else:
            print("\n✗ Some required tables are missing!")

    except Exception as e:
        print(f"Error verifying tables: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    verify_tables()
