"""
SQLite Database Configuration and Initialization
"""
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager

# Database path
DB_DIR = Path("/data/routine/routine-studio-v2/data")
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "routine.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine with SQLite-specific settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite
    echo=False  # Set to True for SQL debugging
)

# Enable foreign keys for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """FastAPI dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database sessions (for non-FastAPI use)"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database and create all tables"""
    import models  # Import models to register them
    Base.metadata.create_all(bind=engine)
    print(f"[Database] Initialized at {DB_PATH}")


def reset_db():
    """Drop all tables and recreate (for development only)"""
    import models
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print(f"[Database] Reset complete at {DB_PATH}")


# Migration helper
def migrate_users_from_json():
    """Migrate existing users.json to database"""
    import json
    from datetime import datetime

    users_file = DB_DIR / "users.json"
    if not users_file.exists():
        print("[Migration] No users.json found, skipping migration")
        return

    with open(users_file, "r") as f:
        users_data = json.load(f)

    from models import User

    with get_db_context() as db:
        migrated = 0
        for user_id, user_info in users_data.items():
            # Check if user already exists
            existing = db.query(User).filter(User.id == user_id).first()
            if existing:
                continue

            user = User(
                id=user_id,
                username=user_info.get("username"),
                password_hash=user_info.get("password"),
                name=user_info.get("name"),
                role=user_info.get("role", "VIEWER"),
                is_approved=user_info.get("is_approved", False),
                created_at=datetime.fromisoformat(user_info.get("created_at", datetime.utcnow().isoformat()))
            )
            db.add(user)
            migrated += 1

        print(f"[Migration] Migrated {migrated} users from users.json")
