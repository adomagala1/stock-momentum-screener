from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

DATABASE_URL = (
    f"postgresql+psycopg2://{settings.pg_user}:{settings.pg_password}"
    f"@{settings.pg_host}:{settings.pg_port}/{settings.pg_db}"
)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
