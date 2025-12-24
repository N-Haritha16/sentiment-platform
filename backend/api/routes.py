from fastapi import APIRouter
from sqlalchemy import select
from backend.models.models import SocialMediaPost, SentimentAnalysis
from backend.config import REDIS_URL, REDIS_STREAM_NAME
import redis.asyncio as redis

router = APIRouter()
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

@router.post("/post")
async def submit_post(payload: dict):
    await redis_client.xadd(REDIS_STREAM_NAME, payload)
    return {"status": "queued"}

@router.get("/posts")
async def get_posts():
    from backend.models.models import Base
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from backend.config import DATABASE_URL

    engine = create_async_engine(DATABASE_URL)
    Session = async_sessionmaker(engine)

    async with Session() as session:
        result = await session.execute(
            select(SocialMediaPost, SentimentAnalysis)
            .join(SentimentAnalysis)
        )
        rows = result.all()

    return [
        {
            "content": post.content,
            "sentiment": analysis.sentiment,
            "emotion": analysis.emotion
        }
        for post, analysis in rows
    ]
