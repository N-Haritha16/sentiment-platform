import json
import time
import uuid
import random
import asyncio
from datetime import datetime, timezone
from kafka import KafkaProducer


class DataIngester:
    """
    Publishes simulated social media posts to a Kafka topic
    """

    def __init__(
        self,
        kafka_bootstrap_servers: str,
        topic_name: str,
        posts_per_minute: int = 60
    ):
        """
        Initialize the Kafka data ingester
        """
        self.topic_name = topic_name
        self.posts_per_minute = posts_per_minute
        self.delay = 60 / posts_per_minute

        self.producer = KafkaProducer(
            bootstrap_servers=kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=3
        )

    def generate_post(self) -> dict:
        """
        Generate a realistic social media post
        """
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

    async def publish_post(self, post_data: dict) -> bool:
        """
        Publish a post to Kafka
        """
        try:
            self.producer.send(self.topic_name, post_data)
            self.producer.flush()
            return True
        except Exception as exc:
            print(f"[INGESTER] Failed to publish post: {exc}")
            return False

    async def start(self, duration_seconds: int = None):
        """
        Start generating and publishing posts continuously
        """
        print("[INGESTER] Starting data ingestion...")
        start_time = time.time()

        try:
            while True:
                post = self.generate_post()
                success = await self.publish_post(post)

                if success:
                    print(f"[INGESTER] Published post {post['post_id']}")

                await asyncio.sleep(self.delay)

                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    break

        except KeyboardInterrupt:
            print("[INGESTER] Stopped by user")

        finally:
            self.producer.close()
            print("[INGESTER] Producer closed")
