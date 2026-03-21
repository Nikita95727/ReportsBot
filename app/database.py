from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Float, Date, DateTime,
    UniqueConstraint, create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    user_name = Column(String(255), nullable=False, default="")
    telegram_id = Column(BigInteger, nullable=False)
    has_report = Column(Integer, nullable=False, default=0)  # 0/1
    has_plan = Column(Integer, nullable=False, default=0)  # 0/1
    format_valid = Column(Integer, nullable=False, default=0)  # 0/1
    format_score = Column(Float, nullable=True, default=None)
    clarity_score = Column(Float, nullable=True, default=None)
    execution_score = Column(Float, nullable=True, default=None)
    discipline_score = Column(Float, nullable=True, default=None)
    total_score = Column(Float, nullable=True, default=None)
    status = Column(Integer, nullable=False, default=0)  # 0-3
    comment = Column(Text, nullable=True, default=None)
    raw_text = Column(Text, nullable=True, default=None)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("telegram_id", "date", name="uq_user_date"),
    )


# Engine & session factory
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Get a new DB session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
