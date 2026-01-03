import asyncio
import json
from datetime import datetime
from typing import Dict
import warnings

import redis.asyncio as redis
from backend.services.sentiment_analyser import SentimentAnalyzer
from backend.config import get_settings
from backend.models.models import async_session_factory

# Suppress annoying warnings
warnings.filterwarnings("ignore", category=UserWarning)


class SentimentWorker:
    """
    Consumes posts from Redis Stream and processes them through sentiment analysis
    """

    def __init__(self, redis_client: redis.Redis, db_session_maker, stream_name: str, consumer_group: str) -> None:
        self.redis = redis_client
        self.db_session_maker = db_session_maker
        self.stream_name = stream_name
        self.consumer_group = consumer_group

        # Analyzer used for both sentiment and emotion
        self.analyzer = SentimentAnalyzer(model_type="local")

        self.messages_processed = 0
        self.messages_failed = 0

    async def _ensure_consumer_group(self) -> None:
        """Create consumer group if it doesn't exist"""
        try:
            await self.redis.xadd(self.stream_name, {"_init": "1"}, id="0-0")
        except Exception:
            pass
        try:
            await self.redis.xgroup_create(
                name=self.stream_name,
                groupname=self.consumer_group,
                id="0-0",
                mkstream=True
            )
            print("[WORKER] Consumer group created")
        except redis.ResponseError as exc:
            if "BUSYGROUP" in str(exc):
                print("[WORKER] Consumer group already exists")
            else:
                raise

    async def process_message(self, message_id: str, message_data: Dict[bytes, bytes]) -> bool:
        """Process a single message from Redis Stream"""
        try:
            decoded = {k.decode(): v.decode() for k, v in message_data.items()}
            required_keys = {"post_id", "source", "content", "author", "created_at"}
            if not required_keys.issubset(decoded.keys()):
                await self.redis.xack(self.stream_name, self.consumer_group, message_id)
                self.messages_failed += 1
                return False

            created_at = datetime.fromisoformat(decoded["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            post_data = {
                "post_id": decoded["post_id"],
                "source": decoded["source"],
                "content": decoded["content"],
                "author": decoded["author"],
                "created_at": created_at,
            }

            async with self.db_session_maker() as db_session:
                # Sentiment analysis
                try:
                    sentiment_result = await self.analyzer.analyze_sentiment(post_data["content"])
                except Exception:
                    # fallback to external model if local fails
                    external_analyzer = SentimentAnalyzer(model_type="external")
                    sentiment_result = await external_analyzer.analyze_sentiment(post_data["content"])

                # Emotion analysis
                emotion_result = await self.analyzer.analyze_emotion(post_data["content"])

                # ✅ Local import to avoid circular import
                from processor import save_post_and_analysis
                await save_post_and_analysis(db_session, post_data, sentiment_result, emotion_result)

            await self.redis.xack(self.stream_name, self.consumer_group, message_id)
            self.messages_processed += 1
            print(f"[WORKER] Processed post {post_data['post_id']} (processed={self.messages_processed})")
            return True

        except Exception as exc:
            print(f"[WORKER] Unexpected error for {message_id}: {exc}")
            try:
                await self.redis.xack(self.stream_name, self.consumer_group, message_id)
            except Exception:
                pass
            self.messages_failed += 1
            return False

    async def run(self, batch_size: int = 10, block_ms: int = 5000) -> None:
        """Main loop to consume messages"""
        await self._ensure_consumer_group()
        consumer_name = "worker-1"
        backoff = 1.0

        while True:
            try:
                response = await self.redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=consumer_name,
                    streams={self.stream_name: ">"},
                    count=batch_size,
                    block=block_ms,
                )

                if not response:
                    continue

                tasks = [
                    self.process_message(message_id, message_data)
                    for _stream, messages in response
                    for message_id, message_data in messages
                ]

                if tasks:
                    await asyncio.gather(*tasks)

                backoff = 1.0

            except redis.ConnectionError as exc:
                print(f"[WORKER] Redis connection error: {exc}, retrying in {backoff:.1f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
            except KeyboardInterrupt:
                print("[WORKER] Shutting down gracefully")
                break


if __name__ == "__main__":
    settings = get_settings()
    redis_client = redis.from_url(settings.redis_url, decode_responses=False)

    worker = SentimentWorker(
        redis_client=redis_client,
        db_session_maker=async_session_factory,
        stream_name=settings.redis_stream_name,
        consumer_group=settings.redis_consumer_group,
    )

    print("[WORKER] Started and waiting for messages...")
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        print("[WORKER] Exited via KeyboardInterrupt")
