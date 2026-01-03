import asyncio
from typing import Dict

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.config import get_settings
from backend.services.sentiment_analyser import SentimentAnalyzer
from sqlalchemy import insert
from backend.models.models import SocialMediaPost, SentimentAnalysis


# ===== Dynamic fallback for EmotionAnalyzer =====
try:
    from backend.services.emotion_analyser import EmotionAnalyzer

except ModuleNotFoundError:
    class EmotionAnalyzer:
        """
        Fallback emotion analyzer used when no ML model is available.
        Always returns neutral emotion.
        """

        def __init__(self, *args, **kwargs):
            pass

        async def analyze_emotion(self, text: str) -> dict:
            return {
                "emotion": "neutral",
                "confidence_score": 0.5,
                "model_name": "fallback",
            }




# ===== Import processor correctly =====
# ===== Define save_post_and_analysis directly to avoid circular import =====

async def save_post_and_analysis(
    db_session: AsyncSession,
    post_data: dict,
    sentiment_result: dict,
    emotion_result: dict
):
    try:
        async with db_session.begin():

            # Insert post
            await db_session.execute(
                insert(SocialMediaPost).values(
                    post_id=post_data["post_id"],
                    source=post_data.get("source", "unknown"),
                    content=post_data.get("content", ""),
                    author=post_data.get("author", "anonymous"),
                    created_at=post_data.get("created_at"),
                )
            )

            # 🔐 HARD DEFAULTS (never allow NULLs)
            sentiment_label = sentiment_result.get("sentiment_label") or "neutral"
            confidence_score = sentiment_result.get("confidence_score")
            confidence_score = float(confidence_score) if confidence_score is not None else 0.5
            emotion = emotion_result.get("emotion") or "neutral"

            await db_session.execute(
                insert(SentimentAnalysis).values(
                    post_id=post_data["post_id"],
                    model_name=sentiment_result.get("model_name", "default"),
                    sentiment_label=sentiment_label,
                    confidence_score=confidence_score,
                    emotion=emotion,
                )
            )

        print(f"[DB] Successfully saved post {post_data['post_id']}")

    except Exception as e:
        print(f"[DB] Failed to save post {post_data.get('post_id')}: {e}")

settings = get_settings()

# Initialize analyzers
sentiment_analyser = SentimentAnalyzer()
emotion_analyser = EmotionAnalyzer()


class SentimentWorker:
    """
    Consumes posts from Redis Stream, performs sentiment & emotion analysis,
    and saves results to the database.
    """

    def __init__(self, redis_url: str, stream_name: str, db_session: AsyncSession):
        self.redis_url = redis_url
        self.stream_name = stream_name
        self.db_session = db_session
        self.redis_client = redis.from_url(redis_url)

    async def run(self):
        last_id = "0-0"  # start from the beginning
        while True:
            try:
                response = await self.redis_client.xread(
                    {self.stream_name: last_id},
                    block=1000,  # wait max 1 second if no message
                    count=10
                )

                if not response:
                    await asyncio.sleep(1)
                    continue

                for stream_name, messages in response:
                    for message_id, message_data in messages:
                        last_id = message_id

                        # Convert bytes to strings
                        post_data = {k.decode(): v.decode() for k, v in message_data.items()}

                        # ====== Skip empty posts ======
                        post_text = post_data.get("content", "")  # usually your Redis key is "content"
                        if not post_text.strip():
                            print("Invalid input skipped")
                            continue

                        # ====== Analyze sentiment & emotion ======
                        sentiment_result = await sentiment_analyser.analyze_sentiment(post_text)
                        emotion_result = await emotion_analyser.analyze_emotion(post_text)



                        # ====== Save to database ======
                        try:
                            await save_post_and_analysis(
                                self.db_session, post_data, sentiment_result, emotion_result
                            )
                        except Exception as e:
                            print(f"Failed to save post {post_data.get('post_id')}: {e}")

            except Exception as e:
                print(f"Worker error: {e}")
                await asyncio.sleep(5)  # retry after delay


# ====== Helper to create DB session ======
async def get_db_session() -> AsyncSession:
    engine = create_async_engine(
        settings.DATABASE_URL, echo=False, future=True
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    return async_session()


# ====== Run the worker ======
async def main():
    async with await get_db_session() as db_session:
        worker = SentimentWorker(
            redis_url=settings.REDIS_URL,
            stream_name="posts_stream",
            db_session=db_session
        )
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
