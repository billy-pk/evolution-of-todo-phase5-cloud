import sys
from pathlib import Path

# Add parent directory to Python path so we can import backend modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlmodel import SQLModel, create_engine
from models import Conversation, Message
from config import settings


def run_migration():
    """Create conversations and messages tables"""
    engine = create_engine(settings.DATABASE_URL)

    # Create tables (only new ones; existing tables unchanged)
    SQLModel.metadata.create_all(engine, tables=[
        Conversation.__table__,
        Message.__table__
    ])

    print("✅ Migration complete: conversations and messages tables created")


if __name__ == "__main__":
    run_migration()
