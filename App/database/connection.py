from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from App.core.config import DATABASE_URL



engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass
