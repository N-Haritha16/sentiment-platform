import json
import asyncio
import logging
from kafka import KafkaConsumer
from sqlalchemy.orm import sessionmaker
from services.sentiment_analyzer import SentimentAnalyzer
from processor import save_post_and_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentiment-worker")


class SentimentWorker:
    """
    Consumes posts from Kafka and processes them through sentiment analysis
    """

    def __init__(
        self,
        kafka_bootstrap_servers: str,
        topic_name: str,
        consumer_group: str,
        db_session_maker: sessionmaker,
    ):
        self.consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=kafka_bootstrap_servers,
            group_id=consumer_group,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )

        self.db_session_maker = db_session_maker
        self.sentiment_analyzer = SentimentAnalyzer(model_type="local")
        self.backup_analyzer = SentimentAnalyzer(model_type="external")

        self.processed = 0
        self.errors = 0

    # --------------------------------------------------

    async def process_message(self, message) -> bool:
        """
        Process a single Kafka message
        """
        post = message.value

        if not post or "content" not in post:
            logger.warning("Invalid message, skipping")
            return True

        try:
            sentiment = await self.sentiment_analyzer.analyze_sentiment(
                post["content"]
            )
            emotion = await self.sentiment_analyzer.analyze_emotion(
                post["content"]
            )
        except Exception:
            try:
                sentiment = await self.backup_analyzer.analyze_sentiment(
                    post["content"]
                )
                emotion = await self.backup_analyzer.analyze_emotion(
                    post["content"]
                )
            except Exception as exc:
                logger.error(f"Analysis failed: {exc}")
                self.errors += 1
                return False

        session = self.db_session_maker()
        try:
            save_post_and_analysis(session, post, sentiment, emotion)
            session.commit()
            self.processed += 1
            return True
        except Exception as exc:
            session.rollback()
            logger.error(f"DB error: {exc}")
            self.errors += 1
            return False
        finally:
            session.close()

    # --------------------------------------------------

    async def run(self):
        """
        Main worker loop
        """
        logger.info("Sentiment worker started")

        try:
            for message in self.consumer:
                success = await self.process_message(message)

                if success:
                    self.consumer.commit()

                if self.processed % 10 == 0 and self.processed > 0:
                    logger.info(
                        f"Processed={self.processed}, Errors={self.errors}"
                    )

        except KeyboardInterrupt:
            logger.info("Worker shutting down gracefully")

        finally:
            self.consumer.close()
            logger.info("Kafka consumer closed")
