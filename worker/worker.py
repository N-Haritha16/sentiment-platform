import asyncio
import logging
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.config import DATABASE_URL, REDIS_URL, REDIS_STREAM_NAME
from services.sentiment_analyser import SentimentAnalyzer
from processor import save_post_and_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentiment-worker")

engine = create_async_engine(DATABASE_URL)
Session = async_sessionmaker(engine, expire_on_commit=False)

class SentimentWorker:
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)
        self.analyzer = SentimentAnalyzer()

    async def run(self):
        last_id = "0"
        logger.info("Worker started")

        while True:
            streams = await self.redis.xread(
                {REDIS_STREAM_NAME: last_id},
                block=1000
            )

            for _, messages in streams:
                for msg_id, data in messages:
                    sentiment = await self.analyzer.analyze_sentiment(data["content"])
                    emotion = await self.analyzer.analyze_emotion(data["content"])

                    async with Session() as session:
                        await save_post_and_analysis(
                            session,
                            data,
                            sentiment,
                            emotion
                        )

                    last_id = msg_id
                    logger.info(f"Processed {msg_id}")

            await asyncio.sleep(0.2)

if __name__ == "__main__":
    asyncio.run(SentimentWorker().run())
