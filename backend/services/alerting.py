import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.models.models import SocialMediaPost, SentimentAnalysis, SentimentAlert


class AlertService:
    """
    Monitors sentiment metrics and triggers alerts on anomalies.
    """

    def __init__(self, db_session_maker, redis_client):
        """
        Initialize with configuration from environment variables.

        Loads:
        - ALERT_NEGATIVE_RATIO_THRESHOLD (default: 2.0)
        - ALERT_WINDOW_MINUTES (default: 5)
        - ALERT_MIN_POSTS (default: 10)
        """
        self.db_session_maker = db_session_maker
        self.redis = redis_client

        self.negative_ratio_threshold: float = float(
            os.getenv("ALERT_NEGATIVE_RATIO_THRESHOLD", "2.0")
        )
        self.window_minutes: int = int(os.getenv("ALERT_WINDOW_MINUTES", "5"))
        self.min_posts: int = int(os.getenv("ALERT_MIN_POSTS", "10"))

        # Optional: Redis channel to publish alerts to dashboard / workers
        self.alert_channel = os.getenv("ALERT_CHANNEL", "sentiment_alerts")

    async def check_thresholds(self) -> Optional[dict]:
        """
        Check if current sentiment metrics exceed alert thresholds.

        Logic:
        1. Count positive/negative posts in last ALERT_WINDOW_MINUTES.
        2. If total posts < ALERT_MIN_POSTS, return None (not enough data).
        3. Calculate ratio = negative_count / positive_count.
        4. If ratio > ALERT_NEGATIVE_RATIO_THRESHOLD, trigger alert.
        """
        async with self.db_session_maker() as db:  # type: AsyncSession
            now = datetime.utcnow()
            since = now - timedelta(minutes=self.window_minutes)

            # Aggregate sentiment counts from SentimentAnalysis within window
            query = (
                select(
                    func.sum(
                        func.case(
                            (SentimentAnalysis.sentiment_label == "positive", 1),
                            else_=0,
                        )
                    ).label("positive"),
                    func.sum(
                        func.case(
                            (SentimentAnalysis.sentiment_label == "negative", 1),
                            else_=0,
                        )
                    ).label("negative"),
                    func.sum(
                        func.case(
                            (SentimentAnalysis.sentiment_label == "neutral", 1),
                            else_=0,
                        )
                    ).label("neutral"),
                    func.count(SentimentAnalysis.id).label("total"),
                )
                .join(
                    SocialMediaPost,
                    SocialMediaPost.post_id == SentimentAnalysis.post_id,
                )
                .where(SentimentAnalysis.analyzed_at >= since)
            )

            row = (await db.execute(query)).one_or_none()
            if row:
                positive_count, negative_count, neutral_count, total_count = row
            else:
                positive_count = negative_count = neutral_count = total_count = 0

            # Not enough data
            if total_count < self.min_posts:
                return None

            # Avoid division by zero
            if positive_count == 0:
                # If there are negative posts and zero positive, treat as infinite ratio
                if negative_count > 0:
                    ratio = float("inf")
                else:
                    ratio = 0.0
            else:
                ratio = negative_count / max(positive_count, 1)

            if ratio <= self.negative_ratio_threshold:
                return None

            alert_data: Dict[str, Any] = {
                "alert_triggered": True,
                "alert_type": "high_negative_ratio",
                "threshold": self.negative_ratio_threshold,
                "actual_ratio": ratio,
                "window_minutes": self.window_minutes,
                "metrics": {
                    "positive_count": int(positive_count),
                    "negative_count": int(negative_count),
                    "neutral_count": int(neutral_count),
                    "total_count": int(total_count),
                },
                "timestamp": now.replace(microsecond=0).isoformat() + "Z",
            }

            return alert_data

    async def save_alert(self, alert_data: dict) -> int:
        """
        Save alert to database and return its ID.
        """
        async with self.db_session_maker() as db:  # type: AsyncSession
            alert = SentimentAlert(
                alert_type=alert_data.get("alert_type"),
                threshold_value=alert_data.get("threshold"),
                actual_value=alert_data.get("actual_ratio"),
                window_minutes=alert_data.get("window_minutes"),
                positive_count=alert_data["metrics"]["positive_count"],
                negative_count=alert_data["metrics"]["negative_count"],
                neutral_count=alert_data["metrics"]["neutral_count"],
                total_count=alert_data["metrics"]["total_count"],
                created_at=datetime.utcnow(),
                raw_payload=alert_data,  # assuming JSON / JSONB column
            )

            db.add(alert)
            await db.commit()
            await db.refresh(alert)

            # Optionally publish to Redis so dashboards can react
            try:
                await self.redis.publish(self.alert_channel, json.dumps(alert_data))
            except Exception:
                # Alert persistence is primary; pub/sub failure is non-fatal
                pass

            return alert.id

    async def run_monitoring_loop(self, check_interval_seconds: int = 60):
        """
        Continuously monitor and trigger alerts.
        """
        while True:
            try:
                alert = await self.check_thresholds()
                if alert and alert.get("alert_triggered"):
                    await self.save_alert(alert)
            except Exception:
                # In production, log this exception with proper logger
                pass

            await asyncio.sleep(check_interval_seconds)
