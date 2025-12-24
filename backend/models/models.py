from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    Text,
    JSON
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from backend.config import DATABASE_URL

Base = declarative_base()

engine = create_async_engine(
   engine = create_async_engine(
    DATABASE_URL,
    echo=False
   )
)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False
)


class SocialMediaPost(Base):
    __tablename__ = "social_media_posts"

    id = Column(Integer, primary_key=True)
    post_id = Column(String, unique=True, index=True)
    source = Column(String, index=True)
    content = Column(Text)
    author = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    ingested_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship(
        "SentimentAnalysis",
        back_populates="post",
        cascade="all, delete-orphan",
        uselist=False
    )


class SentimentAnalysis(Base):
    __tablename__ = "sentiment_analysis"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("social_media_posts.id"))
    sentiment_label = Column(String, index=True)
    sentiment_score = Column(Float)
    emotion = Column(String)
    emotion_score = Column(Float)
    model_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("SocialMediaPost", back_populates="analysis")


class SentimentAlert(Base):
    __tablename__ = "sentiment_alerts"

    id = Column(Integer, primary_key=True)
    alert_type = Column(String)
    threshold = Column(Float)
    actual_ratio = Column(Float)
    window_minutes = Column(Integer)
    metrics = Column(JSON)
    triggered_at = Column(DateTime, default=datetime.utcnow)
