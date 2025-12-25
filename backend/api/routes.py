from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any

import asyncio
import json

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models.models import (
    SocialMediaPost,
    SentimentAnalysis,
    SentimentAlert,
    get_db_session,
)
from config import get_settings
from services.aggregator import SentimentAggregator

settings = get_settings()
router = APIRouter()


async def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True,
    )


@router.get("/api/health")
async def health_check(
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Check system health and connectivity.
    """
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)

    db_status = "disconnected"
    redis_status = "disconnected"
    total_posts = 0
    total_analyses = 0
    recent_posts_1h = 0

    # Database checks
    try:
        await db.execute(select(1))
        db_status = "connected"

        total_posts = await db.scalar(select(func.count(SocialMediaPost.id))) or 0
        total_analyses = await db.scalar(select(func.count(SentimentAnalysis.id))) or 0
        recent_posts_1h = (
            await db.scalar(
                select(func.count(SocialMediaPost.id)).where(
                    SocialMediaPost.created_at >= one_hour_ago
                )
            )
            or 0
        )
    except Exception:
        db_status = "disconnected"

    # Redis check
    try:
        pong = await redis_client.ping()
        redis_status = "connected" if pong else "disconnected"
    except Exception:
        redis_status = "disconnected"

    # Overall status and HTTP code
    if db_status == "connected" and redis_status == "connected":
        overall_status = "healthy"
        status_code = 200
    elif db_status == "disconnected" and redis_status == "disconnected":
        overall_status = "unhealthy"
        status_code = 503
    else:
        overall_status = "degraded"
        status_code = 503

    payload = {
        "status": overall_status,
        "timestamp": now.replace(microsecond=0).isoformat() + "Z",
        "services": {
            "database": db_status,
            "redis": redis_status,
        },
        "stats": {
            "total_posts": total_posts,
            "total_analyses": total_analyses,
            "recent_posts_1h": recent_posts_1h,
        },
    }
    return JSONResponse(status_code=status_code, content=payload)


@router.get("/api/posts")
async def get_posts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    source: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Retrieve posts with filtering and pagination.
    """
    # Join posts + analysis
    query = (
        select(SocialMediaPost, SentimentAnalysis)
        .join(
            SentimentAnalysis,
            SocialMediaPost.post_id == SentimentAnalysis.post_id,
            isouter=True,
        )
    )

    filters = []
    if source:
        filters.append(SocialMediaPost.source == source)
    if sentiment:
        filters.append(SentimentAnalysis.sentiment_label == sentiment)
    if start_date:
        filters.append(SocialMediaPost.created_at >= start_date)
    if end_date:
        filters.append(SocialMediaPost.created_at <= end_date)

    if filters:
        query = query.where(and_(*filters))

    # Total count
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query) or 0

    # Order + pagination
    query = query.order_by(SocialMediaPost.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(query)).all()

    posts_data: List[Dict[str, Any]] = []
    for post, analysis in rows:
        posts_data.append(
            {
                "post_id": post.post_id,
                "source": post.source,
                "content": post.content,
                "author": post.author,
                "created_at": post.created_at.replace(microsecond=0).isoformat() + "Z",
                "sentiment": {
                    "label": analysis.sentiment_label if analysis else None,
                    "confidence": float(analysis.confidence_score) if analysis else None,
                    "emotion": analysis.emotion if analysis else None,
                    "model_name": analysis.model_name if analysis else None,
                }
                if analysis
                else None,
            }
        )

    return {
        "posts": posts_data,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "source": source,
            "sentiment": sentiment,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
    }


@router.get("/api/sentiment/aggregate")
async def get_sentiment_aggregate(
    period: str = Query(..., regex="^(minute|hour|day)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get sentiment counts aggregated by time period.
    """
    if end_date is None:
        end_dt = datetime.utcnow()
    else:
        end_dt = end_date

    if start_date is None:
        start_dt = end_dt - timedelta(hours=24)
    else:
        start_dt = start_date

    if period == "minute":
        bucket_expr = func.date_trunc("minute", SentimentAnalysis.analyzed_at)
    elif period == "day":
        bucket_expr = func.date_trunc("day", SentimentAnalysis.analyzed_at)
    else:
        bucket_expr = func.date_trunc("hour", SentimentAnalysis.analyzed_at)

    query = (
        select(
            bucket_expr.label("bucket"),
            func.sum(
                func.case(
                    (SentimentAnalysis.sentiment_label == "positive", 1),
                    else_=0,
                )
            ).label("positive_count"),
            func.sum(
                func.case(
                    (SentimentAnalysis.sentiment_label == "negative", 1),
                    else_=0,
                )
            ).label("negative_count"),
            func.sum(
                func.case(
                    (SentimentAnalysis.sentiment_label == "neutral", 1),
                    else_=0,
                )
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
            positive_pct = (positive_count / total_count) * 100.0
            negative_pct = (negative_count / total_count) * 100.0
            neutral_pct = (neutral_count / total_count) * 100.0
        else:
            positive_pct = negative_pct = neutral_pct = 0.0

        data.append(
            {
                "timestamp": bucket.replace(microsecond=0).isoformat() + "Z",
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "total_count": total_count,
                "positive_percentage": positive_pct,
                "negative_percentage": negative_pct,
                "neutral_percentage": neutral_pct,
                "average_confidence": float(avg_confidence) if avg_confidence is not None else 0.0,
            }
        )

    summary = {
        "total_posts": total_posts,
        "positive_total": total_positive,
        "negative_total": total_negative,
        "neutral_total": total_neutral,
    }

    return {
        "period": period,
        "start_date": start_dt.replace(microsecond=0).isoformat() + "Z",
        "end_date": end_dt.replace(microsecond=0).isoformat() + "Z",
        "data": data,
        "summary": summary,
    }


@router.get("/api/sentiment/distribution")
async def get_sentiment_distribution(
    hours: int = Query(24, ge=1, le=168),
    source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get current sentiment distribution for dashboard.
    """
    now = datetime.utcnow()
    since = now - timedelta(hours=hours)

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
        positive_pct = (positive / total) * 100.0
        negative_pct = (negative / total) * 100.0
        neutral_pct = (neutral / total) * 100.0
    else:
        positive_pct = negative_pct = neutral_pct = 0.0

    # placeholder top_emotions in required shape
    top_emotions: Dict[str, int] = {
        "joy": 0,
        "anger": 0,
        "sadness": 0,
        "neutral": neutral,
        "surprise": 0,
    }

    return {
        "timeframe_hours": hours,
        "source": source,
        "distribution": {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
        },
        "total": total,
        "percentages": {
            "positive": positive_pct,
            "negative": negative_pct,
            "neutral": neutral_pct,
        },
        "top_emotions": top_emotions,
        "cached": False,
        "cached_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/ws/sentiment")
async def websocket_endpoint(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db_session),
):
    """
    WebSocket endpoint for real-time sentiment updates.
    """
    await manager.connect(websocket)
    redis_client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True,
    )
    aggregator = SentimentAggregator(redis_client)

    try:
        # Type 1: Connection Confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "message": "Connected to sentiment stream",
                "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            }
        )

        pubsub = redis_client.pubsub()
        await pubsub.subscribe("sentiment_updates")

        async def metrics_loop() -> None:
            # Type 3: Metrics Update (every 30 seconds)
            while True:
                metrics_1 = await aggregator.get_distribution(
                    db, hours=1, source=None, use_cache=False
                )
                metrics_60 = await aggregator.get_distribution(
                    db, hours=60, source=None, use_cache=False
                )
                metrics_24 = await aggregator.get_distribution(
                    db, hours=24, source=None, use_cache=False
                )

                await manager.broadcast(
                    {
                        "type": "metrics_update",
                        "data": {
                            "last_minute": {
                                "positive": metrics_1["distribution"]["positive"],
                                "negative": metrics_1["distribution"]["negative"],
                                "neutral": metrics_1["distribution"]["neutral"],
                                "total": metrics_1["total"],
                            },
                            "last_hour": {
                                "positive": metrics_60["distribution"]["positive"],
                                "negative": metrics_60["distribution"]["negative"],
                                "neutral": metrics_60["distribution"]["neutral"],
                                "total": metrics_60["total"],
                            },
                            "last_24_hours": {
                                "positive": metrics_24["distribution"]["positive"],
                                "negative": metrics_24["distribution"]["negative"],
                                "neutral": metrics_24["distribution"]["neutral"],
                                "total": metrics_24["total"],
                            },
                        },
                        "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                    }
                )
                await asyncio.sleep(30)

        async def updates_loop() -> None:
            # Type 2: New Post Update
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                    if payload.get("type") == "post":
                        data = payload.get("data", {})
                        await manager.broadcast(
                            {
                                "type": "new_post",
                                "data": {
                                    "post_id": data.get("post_id"),
                                    "content": data.get("content", "")[:100],
                                    "source": data.get("source"),
                                    "sentiment_label": data.get("sentiment_label"),
                                    "confidence_score": data.get("confidence_score"),
                                    "emotion": data.get("emotion"),
                                    "timestamp": data.get("timestamp"),
                                },
                            }
                        )
                    else:
                        await manager.broadcast(payload)
                except Exception:
                    continue

        await asyncio.gather(metrics_loop(), updates_loop())

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        await redis_client.close()
