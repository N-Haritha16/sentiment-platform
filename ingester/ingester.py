import asyncio
import uuid
import random
from datetime import datetime, timezone
import redis.asyncio as redis
from backend.config import (
    REDIS_URL,
    REDIS_STREAM_NAME,
)

class DataIngester:
    def __init__(self, posts_per_minute: int = 60):
        self.delay = 60 / posts_per_minute
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)

    def generate_post(self) -> dict:
        positive_templates = [
            "I absolutely love this product, it works amazingly well!",
            "Such a great experience, I would highly recommend it to everyone.",
            "Amazing service and fantastic quality. Very satisfied!"
        ]

        neutral_templates = [
            "I purchased this item yesterday and started using it today.",
            "This update was released earlier this morning.",
            "The product arrived on time and matches the description."
        ]

        negative_templates = [
            "I hate how poorly this works. Very disappointed.",
            "Terrible experience, the quality is unacceptable.",
            "This is the worst service I have used in a long time."
        ]

        sentiment_bucket = random.choices(
            ["positive", "neutral", "negative"],
            weights=[40, 30, 30],
            k=1
        )[0]

        if sentiment_bucket == "positive":
            content = random.choice(positive_templates)
        elif sentiment_bucket == "neutral":
            content = random.choice(neutral_templates)
        else:
            content = random.choice(negative_templates)

        return {
            "post_id": f"post_{uuid.uuid4().hex}",
            "source": random.choice(["twitter", "reddit", "news"]),
            "content": content,
            "author": f"user_{random.randint(1000, 9999)}",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    async def start(self):
        while True:
            post = self.generate_post()
            await self.redis.xadd(REDIS_STREAM_NAME, post)
            await asyncio.sleep(self.delay)


if __name__ == "__main__":
    ingester = DataIngester(posts_per_minute=60)
    asyncio.run(ingester.start())
