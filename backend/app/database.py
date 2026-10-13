import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend folder if present
env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
DATABASE_URL = os.getenv("DATABASE_URL")

is_placeholder = bool(
    not DATABASE_URL
    or "@host:5432" in DATABASE_URL
    or "user:password" in DATABASE_URL
    or "your" in DATABASE_URL.lower()
)

if ENVIRONMENT == "production":
    if is_placeholder:
        raise RuntimeError(
            "FATAL [Database]: In production (ENVIRONMENT=production), DATABASE_URL must be set "
            "to a valid hosted PostgreSQL connection string. SQLite fallback is strictly prohibited."
        )
    if not (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgresql+")):
        raise RuntimeError(
            f"FATAL [Database]: In production, DATABASE_URL must be a PostgreSQL connection string. "
            f"Received unsupported scheme. SQLite fallback is strictly prohibited."
        )

# PostgreSQL URL formatting and driver selection
if DATABASE_URL and not is_placeholder:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif DATABASE_URL.startswith("postgresql://") and not DATABASE_URL.startswith("postgresql+"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

    # Hosted Postgres (Neon, Supabase, Render) requires SSL
    if "localhost" not in DATABASE_URL and "127.0.0.1" not in DATABASE_URL:
        if "sslmode" not in DATABASE_URL:
            sep = "&" if "?" in DATABASE_URL else "?"
            DATABASE_URL = f"{DATABASE_URL}{sep}sslmode=require"

elif is_placeholder:
    # Development fallback
    print(f"INFO [Database]: Using local SQLite fallback in {ENVIRONMENT} mode (local_records.db).")
    DATABASE_URL = "sqlite:///./local_records.db"

is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine_kwargs = {"pool_pre_ping": True}
if not is_sqlite:
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
