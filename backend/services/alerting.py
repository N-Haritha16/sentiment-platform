import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func
from backend.models.models import SocialMediaPost, SentimentAnalysis, SentimentAlert, AsyncSession

class AlertService:
    """
    Monitors sentiment metrics and triggers alerts on anomalies
    """

    def __init__(self, db_session_maker, redis_client):
        """
        Initialize with configuration from environment variables
        
        Loads:
        - ALERT_NEGATIVE_RATIO_THRESHOLD (default: 2.0)
        - ALERT_WINDOW_MINUTES (default: 5)
        - ALERT_MIN_POSTS (default: 10)
        """
        self.db_session_maker = db_session_maker
        self.redis_client = redis_client
        self.threshold = float(os.getenv("ALERT_NEGATIVE_RATIO_THRESHOLD", 2.0))
        self.window_minutes = int(os.getenv("ALERT_WINDOW_MINUTES", 5))
        self.min_posts = int(os.getenv("ALERT_MIN_POSTS", 10))

    async def check_thresholds(self) -> Optional[dict]:
        """
        Check if current sentiment metrics exceed alert thresholds
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=self.window_minutes)

        async with self.db_session_maker() as session:  # AsyncSession
            result = await session.execute(
                func.count(SentimentAnalysis.id),
                # Counting positive, negative, neutral
            )
            
            counts_query = (
                session.query(
                    SentimentAnalysis.label,
                    func.count().label("count")
                )
                .join(SocialMediaPost, SocialMediaPost.id == SentimentAnalysis.post_id)
                .filter(SocialMediaPost.created_at >= window_start)
                .group_by(SentimentAnalysis.label)
            )
            rows = await session.execute(counts_query)
            rows = rows.all()

        # Initialize counts
        metrics = {"positive": 0, "negative": 0, "neutral": 0}
        for label, count in rows:
            metrics[label] = count
        metrics["total_count"] = sum(metrics.values())

        if metrics["total_count"] < self.min_posts or metrics["positive"] == 0:
            return None  # Not enough data to trigger alert

        ratio = metrics["negative"] / metrics["positive"]

        if ratio > self.threshold:
            return {
                "alert_triggered": True,
                "alert_type": "high_negative_ratio",
                "threshold": self.threshold,
                "actual_ratio": ratio,
                "window_minutes": self.window_minutes,
                "metrics": metrics,
                "timestamp": now.isoformat()
            }

        return None

    async def save_alert(self, alert_data: dict) -> int:
        """
        Save alert to database
        """
        async with self.db_session_maker() as session:
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

    async def run_monitoring_loop(self, check_interval_seconds: int = 60):
        """
        Continuously monitor and trigger alerts
        """
        while True:
            try:
                alert = await self.check_thresholds()
                if alert:
                    alert_id = await self.save_alert(alert)
                    print(f"[ALERT] Triggered alert {alert_id}: {alert}")
            except Exception as e:
                print(f"[ALERT ERROR] {e}")

            await asyncio.sleep(check_interval_seconds)
