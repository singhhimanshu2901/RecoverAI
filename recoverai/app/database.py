import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Works locally with SQLite by default. For deployment (Render/Railway),
# set DATABASE_URL env var to a Postgres URL and it switches automatically.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./recoverai.db")

# Render (and some other hosts) give postgres:// but SQLAlchemy 2.x needs
# the postgresql:// scheme.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()