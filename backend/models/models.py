from __future__ import annotations

from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, relationship

from config import get_settings


settings = get_settings()
Base = declarative_base()


class SocialMediaPost(Base):
    """
    Table 1: social_media_posts
    Purpose: Store raw social media posts
    """
    __tablename__ = "social_media_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(255), unique=True, index=True, nullable=False)
    source = Column(String(50), index=True, nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)
    ingested_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    analysis = relationship(
        "SentimentAnalysis",
        back_populates="post",
        cascade="all, delete-orphan",
        uselist=False,
    )


class SentimentAnalysis(Base):
    """
    Table 2: sentiment_analysis
    Purpose: Store sentiment analysis results
    """
    __tablename__ = "sentiment_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(
        String(255),
        ForeignKey("social_media_posts.post_id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name = Column(String(100), nullable=False)
    sentiment_label = Column(String(20), nullable=False)  # positive/negative/neutral
    confidence_score = Column(Float, nullable=False)
    emotion = Column(String(50), nullable=True)
    analyzed_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    post = relationship("SocialMediaPost", back_populates="analysis")


class SentimentAlert(Base):
    """
    Table 3: sentiment_alerts
    Purpose: Store triggered alerts
    """
    __tablename__ = "sentiment_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(50), nullable=False)
    threshold_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    post_count = Column(Integer, nullable=False)
    triggered_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    details = Column(JSON, nullable=False)


# Required indexes on frequently queried columns
Index("ix_social_media_posts_post_id", SocialMediaPost.post_id)
Index("ix_social_media_posts_source", SocialMediaPost.source)
Index("ix_social_media_posts_created_at", SocialMediaPost.created_at)
Index("ix_sentiment_analysis_analyzed_at", SentimentAnalysis.analyzed_at)
Index("ix_sentiment_alerts_triggered_at", SentimentAlert.triggered_at)


# Async engine and session factory
DATABASE_URL = settings.database_url  # from config.py / env

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

async def init_models(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)