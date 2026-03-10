from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from .models import Base
from config.config_loader import CONFIG

_db_path = CONFIG["db"]["path"]
engine = create_engine(f"sqlite:///{_db_path}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(engine)


@contextmanager
def get_session():
    """Context manager that yields a SQLAlchemy session and handles commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
