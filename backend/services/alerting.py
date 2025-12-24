import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import (
    SocialMediaPost,
    SentimentAnalysis,
    SentimentAlert
)


class AlertService:
    """
    Monitors sentiment metrics and triggers alerts on anomalies
    """

    def __init__(self, async_session_maker, redis_client=None):
        self.async_session_maker = async_session_maker
        self.redis_client = redis_client

        self.threshold = float(os.getenv("ALERT_NEGATIVE_RATIO_THRESHOLD", 2.0))
        self.window_minutes = int(os.getenv("ALERT_WINDOW_MINUTES", 5))
        self.min_posts = int(os.getenv("ALERT_MIN_POSTS", 10))

    # --------------------------------------------------

    async def check_thresholds(self) -> Optional[dict]:
        """
        Check sentiment ratio for alert triggering
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=self.window_minutes)

        async with self.async_session_maker() as session:  # AsyncSession
            query = (
                select(
                    SentimentAnalysis.sentiment_label,
                    func.count().label("count")
                )
                .join(
                    SocialMediaPost,
                    SocialMediaPost.id == SentimentAnalysis.post_id
                )
                .where(SocialMediaPost.created_at >= window_start)
                .group_by(SentimentAnalysis.sentiment_label)
            )

            rows = (await session.execute(query)).all()

        metrics = {
            "positive": 0,
            "negative": 0,
            "neutral": 0
        }

        for label, count in rows:
            if label in metrics:
                metrics[label] = count

        metrics["total"] = sum(metrics.values())

        if metrics["total"] < self.min_posts or metrics["positive"] == 0:
            return None

        negative_ratio = metrics["negative"] / metrics["positive"]

        if negative_ratio > self.threshold:
            return {
                "alert_triggered": True,
                "alert_type": "high_negative_ratio",
                "threshold": self.threshold,
                "actual_ratio": round(negative_ratio, 2),
                "window_minutes": self.window_minutes,
                "metrics": metrics,
                "timestamp": now.isoformat()
            }

        return None

    # --------------------------------------------------

    async def save_alert(self, alert_data: dict) -> int:
        """
        Persist alert to database
        """
        async with self.async_session_maker() as session:
            alert = SentimentAlert(
                alert_type=alert_data["alert_type"],
                threshold=alert_data["threshold"],
                actual_ratio=alert_data["actual_ratio"],
                window_minutes=alert_data["window_minutes"],
                metrics=alert_data["metrics"],
                triggered_at=datetime.fromisoformat(alert_data["timestamp"])
            )

            session.add(alert)
            await session.commit()
            await session.refresh(alert)
            return alert.id

    # --------------------------------------------------

    async def run_monitoring_loop(self, interval_seconds: int = 60):
        """
        Continuous monitoring loop
        """
        while True:
            try:
                alert = await self.check_thresholds()
                if alert:
                    alert_id = await self.save_alert(alert)
                    print(f"[ALERT] Triggered alert {alert_id}")
            except Exception as exc:
                print(f"[ALERT ERROR] {exc}")

            await asyncio.sleep(interval_seconds)
