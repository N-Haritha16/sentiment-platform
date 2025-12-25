from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import json
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.config import get_settings
from backend.models.models import SocialMediaPost, SentimentAnalysis

settings = get_settings()


class SentimentAggregator:
    """
    Provides aggregated sentiment metrics with optional Redis caching.
    """

    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client
        self.cache_prefix = settings.redis_cache_prefix

    def _aggregate_cache_key(
        self,
        period: str,
        start_dt: datetime,
        end_dt: datetime,
        source: Optional[str],
    ) -> str:
        src = source or "all"
        return f"{self.cache_prefix}:aggregate:{period}:{start_dt.isoformat()}:{end_dt.isoformat()}:{src}"

    def _distribution_cache_key(self, hours: int, source: Optional[str]) -> str:
        src = source or "all"
        return f"{self.cache_prefix}:distribution:{hours}:{src}"

    async def get_aggregate(
        self,
        db: AsyncSession,
        period: str,
        start_dt: datetime,
        end_dt: datetime,
        source: Optional[str],
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        key = self._aggregate_cache_key(period, start_dt, end_dt, source)

        if use_cache:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)

        if period == "minute":
            trunc_expr = func.date_trunc("minute", SentimentAnalysis.analyzed_at)
        elif period == "day":
            trunc_expr = func.date_trunc("day", SentimentAnalysis.analyzed_at)
        else:
            trunc_expr = func.date_trunc("hour", SentimentAnalysis.analyzed_at)

        query = (
            select(
                trunc_expr.label("bucket"),
                func.sum(
                    func.case((SentimentAnalysis.sentiment_label == "positive", 1), else_=0)
                ).label("positive_count"),
                func.sum(
                    func.case((SentimentAnalysis.sentiment_label == "negative", 1), else_=0)
                ).label("negative_count"),
                func.sum(
                    func.case((SentimentAnalysis.sentiment_label == "neutral", 1), else_=0)
                ).label("neutral_count"),
                func.count(SentimentAnalysis.id).label("total_count"),
                func.avg(SentimentAnalysis.confidence_score).label("avg_confidence"),
            )
            .join(SocialMediaPost, SocialMediaPost.post_id == SentimentAnalysis.post_id)
            .where(SentimentAnalysis.analyzed_at >= start_dt)
            .where(SentimentAnalysis.analyzed_at <= end_dt)
            .group_by("bucket")
            .order_by("bucket")
        )

        if source:
            query = query.where(SocialMediaPost.source == source)

        rows = (await db.execute(query)).all()

        data: List[Dict[str, Any]] = []
        total_posts = 0
        total_positive = 0
        total_negative = 0
        total_neutral = 0

        for (
            bucket,
            positive_count,
            negative_count,
            neutral_count,
            total_count,
            avg_confidence,
        ) in rows:
            total_posts += total_count
            total_positive += positive_count
            total_negative += negative_count
            total_neutral += neutral_count

            if total_count > 0:
                pos_pct = positive_count / total_count * 100.0
                neg_pct = negative_count / total_count * 100.0
                neu_pct = neutral_count / total_count * 100.0
            else:
                pos_pct = neg_pct = neu_pct = 0.0

            data.append(
                {
                    "timestamp": bucket.isoformat(),
                    "positive_count": positive_count,
                    "negative_count": negative_count,
                    "neutral_count": neutral_count,
                    "total_count": total_count,
                    "positive_percentage": pos_pct,
                    "negative_percentage": neg_pct,
                    "neutral_percentage": neu_pct,
                    "average_confidence": float(avg_confidence) if avg_confidence is not None else 0.0,
                }
            )

        summary = {
            "total_posts": total_posts,
            "positive_total": total_positive,
            "negative_total": total_negative,
            "neutral_total": total_neutral,
        }

        result = {
            "period": period,
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "data": data,
            "summary": summary,
        }

        if use_cache:
            await self.redis.setex(key, 60, json.dumps(result))

        return result

    async def get_distribution(
        self,
        db: AsyncSession,
        hours: int,
        source: Optional[str],
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        since = now - timedelta(hours=hours)
        key = self._distribution_cache_key(hours, source)

        if use_cache:
            cached = await self.redis.get(key)
            if cached:
                dist = json.loads(cached)
                dist["cached"] = True
                dist["cached_at"] = now.isoformat()
                return dist

        query = (
            select(
                func.sum(
                    func.case((SentimentAnalysis.sentiment_label == "positive", 1), else_=0)
                ).label("positive"),
                func.sum(
                    func.case((SentimentAnalysis.sentiment_label == "negative", 1), else_=0)
                ).label("negative"),
                func.sum(
                    func.case((SentimentAnalysis.sentiment_label == "neutral", 1), else_=0)
                ).label("neutral"),
                func.count(SentimentAnalysis.id).label("total"),
            )
            .join(SocialMediaPost, SocialMediaPost.post_id == SentimentAnalysis.post_id)
            .where(SentimentAnalysis.analyzed_at >= since)
        )

        if source:
            query = query.where(SocialMediaPost.source == source)

        row = (await db.execute(query)).one_or_none()
        if row:
            positive, negative, neutral, total = row
        else:
            positive = negative = neutral = total = 0

        if total > 0:
            pos_pct = positive / total * 100.0
            neg_pct = negative / total * 100.0
            neu_pct = neutral / total * 100.0
        else:
            pos_pct = neg_pct = neu_pct = 0.0

        result = {
            "timeframe_hours": hours,
            "source": source,
            "distribution": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "total": total,
                "percentages": {
                    "positive": pos_pct,
                    "negative": neg_pct,
                    "neutral": neu_pct,
                },
                "top_emotions": {},  # can be extended later
            },
            "cached": False,
            "cached_at": now.isoformat(),
        }

        if use_cache:
            await self.redis.setex(key, 60, json.dumps(result))

        return result
