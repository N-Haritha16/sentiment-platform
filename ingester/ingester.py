import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, Optional

import redis.asyncio as redis

import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")


settings = get_settings()


class DataIngester:
    """
    Publishes simulated social media posts to Redis Streams.
    """

    def __init__(self, redis_client: redis.Redis, stream_name: str, posts_per_minute: int = 60) -> None:
        """
        Initialize the ingester.
        """
        self.redis = redis_client
        self.stream_name = stream_name
        self.posts_per_minute = posts_per_minute

        self._positive_templates = [
            "I absolutely love {product}!",
            "{product} is amazing and exceeded my expectations.",
            "Great experience using {product} today.",
        ]
        self._negative_templates = [
            "Very disappointed with {product}.",
            "Terrible experience using {product}.",
            "I hate how {product} works right now.",
        ]
        self._neutral_templates = [
            "Just tried {product} for the first time.",
            "Received {product} today.",
            "Using {product} for the first time.",
        ]
        self._products = [
            "iPhone 16",
            "Tesla Model 3",
            "ChatGPT",
            "Netflix",
            "Amazon Prime",
            "PlayStation 6",
        ]

    def generate_post(self) -> Dict[str, str]:
        """
        Generate a single realistic post with varied sentiment.

        Returns dict with keys: post_id, source, content, author, created_at.
        """
        sentiment_roll = random.random()
        if sentiment_roll < 0.4:
            template = random.choice(self._positive_templates)
        elif sentiment_roll < 0.7:
            template = random.choice(self._neutral_templates)
        else:
            template = random.choice(self._negative_templates)

        product = random.choice(self._products)
        content = template.format(product=product)

        post_id = f"post_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{random.randint(1000, 9999)}"
        source = random.choice(["reddit", "twitter"])
        author = f"user_{random.randint(1000, 9999)}"
        created_at = datetime.now(timezone.utc).isoformat()

        return {
            "post_id": post_id,
            "source": source,
            "content": content,
            "author": author,
            "created_at": created_at,
        }

    async def publish_post(self, post_data: dict) -> bool:
        """
        Publish a single post to Redis Stream using XADD.
        """
        try:
            await self.redis.xadd(
                name=self.stream_name,
                fields=post_data,
                maxlen=None,
                approximate=False,
            )
            return True
        except Exception:
            return False

    async def start(self, duration_seconds: Optional[int] = None) -> None:
        """
        Start continuous post generation and publishing.
        """
        if self.posts_per_minute <= 0:
            delay = 1.0
        else:
            delay = 60.0 / float(self.posts_per_minute)

        start_time = datetime.now(timezone.utc)
        while True:
            if duration_seconds is not None:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= duration_seconds:
                    break

            post = self.generate_post()
            await self.publish_post(post)
            await asyncio.sleep(delay)


async def main() -> None:
    client = redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)
    ingester = DataIngester(
        redis_client=client,
        stream_name=settings.redis_stream_name,
        posts_per_minute=30,
    )
    await ingester.start()


if __name__ == "__main__":
    asyncio.run(main())
