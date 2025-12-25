import asyncio
import json
from datetime import datetime
from typing import Any, Dict

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from services.sentiment_analyzer import SentimentAnalyzer
from worker.processor import save_post_and_analysis


class SentimentWorker:
    """
    Consumes posts from Redis Stream and processes them through sentiment analysis
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        db_session_maker,
        stream_name: str,
        consumer_group: str,
    ) -> None:
        """
        Initialize worker with necessary dependencies
        """
        self.redis = redis_client
        self.db_session_maker = db_session_maker
        self.stream_name = stream_name
        self.consumer_group = consumer_group

        # analyzers
        self.local_analyzer = SentimentAnalyzer(model_type="local")
        self.external_analyzer = SentimentAnalyzer(model_type="external")

        # stats
        self.messages_processed = 0
        self.messages_failed = 0

    async def _ensure_consumer_group(self) -> None:
        try:
            await self.redis.xgroup_create(
                name=self.stream_name,
                groupname=self.consumer_group,
                id="0-0",
                mkstream=True,
            )
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    async def process_message(self, message_id: str, message_data: Dict[bytes, bytes]) -> bool:
        """
        Process a single message from the stream
        """
        try:
            decoded: Dict[str, Any] = {k.decode(): v.decode() for k, v in message_data.items()}
            required_keys = {"post_id", "source", "content", "author", "created_at"}
            if not required_keys.issubset(decoded.keys()):
                # invalid payload → ack and skip
                await self.redis.xack(self.stream_name, self.consumer_group, message_id)
                self.messages_failed += 1
                return False

            # parse created_at
            created_at = datetime.fromisoformat(decoded["created_at"].replace("Z", "+00:00"))

            post_data = {
                "post_id": decoded["post_id"],
                "source": decoded["source"],
                "content": decoded["content"],
                "author": decoded["author"],
                "created_at": created_at,
            }

            async with self.db_session_maker() as db_session:  # type: AsyncSession
                try:
                    # 2. Run sentiment analysis (local by default, fallback external)
                    try:
                        sentiment_result = await self.local_analyzer.analyze_sentiment(post_data["content"])
                    except Exception:
                        sentiment_result = await self.external_analyzer.analyze_sentiment(post_data["content"])

                    # 3. Run emotion detection
                    emotion_result = await self.local_analyzer.analyze_emotion(post_data["content"])

                    # 4–5. Save post and analysis
                    await save_post_and_analysis(
                        db_session=db_session,
                        post_data=post_data,
                        sentiment_result=sentiment_result,
                        emotion_result=emotion_result,
                    )
                except Exception as db_exc:
                    # DB failure → do NOT ack, so message can be retried
                    self.messages_failed += 1
                    print(f"[WORKER] DB error for {message_id}: {db_exc}")
                    return False

            # Optional: publish summary for WebSocket
            preview = post_data["content"][:120]
            try:
                await self.redis.publish(
                    "sentiment_updates",
                    json.dumps(
                        {
                            "type": "post",
                            "data": {
                                "post_id": post_data["post_id"],
                                "content": preview,
                                "source": post_data["source"],
                                "sentiment_label": sentiment_result["sentiment_label"],
                                "confidence_score": sentiment_result["confidence_score"],
                                "emotion": emotion_result.get("emotion"),
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                        }
                    ),
                )
            except Exception:
                # publishing failure shouldn't break processing
                pass

            # 6. Acknowledge message
            await self.redis.xack(self.stream_name, self.consumer_group, message_id)
            self.messages_processed += 1
            return True

        except Exception as exc:
            # Unknown error → ack to avoid poison messages looping forever
            print(f"[WORKER] Unexpected error for {message_id}: {exc}")
            try:
                await self.redis.xack(self.stream_name, self.consumer_group, message_id)
            except Exception:
                pass
            self.messages_failed += 1
            return False

    async def run(self, batch_size: int = 10, block_ms: int = 5000) -> None:
        """
        Main worker loop - continuously consume and process messages
        """
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

                tasks = []
                for _stream, messages in response:
                    for message_id, message_data in messages:
                        tasks.append(self.process_message(message_id, message_data))

                if tasks:
                    await asyncio.gather(*tasks)
                    if self.messages_processed % 50 == 0:
                        print(
                            f"[WORKER] processed={self.messages_processed} "
                            f"failed={self.messages_failed}"
                        )

                backoff = 1.0  # reset on success

            except redis.ConnectionError as exc:
                print(f"[WORKER] Redis connection error: {exc}, retrying in {backoff:.1f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
            except KeyboardInterrupt:
                print("[WORKER] Shutting down gracefully")
                break
