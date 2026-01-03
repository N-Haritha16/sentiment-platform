from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import asyncio
import json

import redis.asyncio as redis
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case

from models.models import (
    SocialMediaPost,
    SentimentAnalysis,
    get_db_session,
)
from config import get_settings
from services.aggregator import SentimentAggregator


settings = get_settings()
router = APIRouter()


# ========================= REDIS =========================

async def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True,
    )


# ========================= HEALTH =========================

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)

    db_status = "disconnected"
    redis_status = "disconnected"

    total_posts = total_analyses = recent_posts_1h = 0

    try:
        await db.execute(select(1))
        db_status = "connected"

        total_posts = await db.scalar(select(func.count(SocialMediaPost.id))) or 0
        total_analyses = await db.scalar(select(func.count(SentimentAnalysis.id))) or 0
        recent_posts_1h = await db.scalar(
            select(func.count(SocialMediaPost.id))
            .where(SocialMediaPost.created_at >= one_hour_ago)
        ) or 0
    except Exception:
        pass

    try:
        pong = await redis_client.ping()
        redis_status = "connected" if pong else "disconnected"
    except Exception:
        pass

    overall = (
        "healthy" if db_status == redis_status == "connected"
        else "degraded" if db_status == "connected" or redis_status == "connected"
        else "unhealthy"
    )

    return JSONResponse(
        status_code=200 if overall == "healthy" else 503,
        content={
            "status": overall,
            "timestamp": now.isoformat() + "Z",
            "services": {"database": db_status, "redis": redis_status},
            "stats": {
                "total_posts": total_posts,
                "total_analyses": total_analyses,
                "recent_posts_1h": recent_posts_1h,
            },
        },
    )


# ========================= POSTS =========================

@router.get("/posts")
async def get_posts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    source: Optional[str] = None,
    sentiment: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
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

    if filters:
        query = query.where(and_(*filters))

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0

    rows = (
        await db.execute(
            query.order_by(SocialMediaPost.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    return {
        "posts": [
            {
                "post_id": p.post_id,
                "source": p.source,
                "content": p.content,
                "author": p.author,
                "created_at": p.created_at.isoformat() + "Z",
                "sentiment": {
                    "label": a.sentiment_label,
                    "confidence": float(a.confidence_score) if a else None,
                    "emotion": a.emotion if a else None,
                } if a else None,
            }
            for p, a in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ========================= AGGREGATE =========================

@router.get("/sentiment/aggregate")
async def get_sentiment_aggregate(
    period: str = Query(..., regex="^(minute|hour|day)$"),
    db: AsyncSession = Depends(get_db_session),
):
    bucket = {
        "minute": func.date_trunc("minute", SentimentAnalysis.analyzed_at),
        "hour": func.date_trunc("hour", SentimentAnalysis.analyzed_at),
        "day": func.date_trunc("day", SentimentAnalysis.analyzed_at),
    }[period]

    query = (
        select(
            bucket.label("bucket"),
            func.sum(case((SentimentAnalysis.sentiment_label == "positive", 1), else_=0)).label("positive"),
            func.sum(case((SentimentAnalysis.sentiment_label == "negative", 1), else_=0)).label("negative"),
            func.sum(case((SentimentAnalysis.sentiment_label == "neutral", 1), else_=0)).label("neutral"),
            func.count(SentimentAnalysis.id).label("total"),
        )
        .join(SocialMediaPost, SocialMediaPost.post_id == SentimentAnalysis.post_id)
        .group_by("bucket")
        .order_by("bucket")
    )

    rows = (await db.execute(query)).all()

    return {
        "period": period,
        "data": [
            {
                "timestamp": b.isoformat() + "Z",
                "positive": p,
                "negative": n,
                "neutral": ne,
                "total": t,
            }
            for b, p, n, ne, t in rows
        ],
    }


# ========================= DISTRIBUTION =========================

@router.get("/sentiment/distribution")
async def get_sentiment_distribution(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db_session),
):
    since = datetime.utcnow() - timedelta(hours=hours)

    query = (
        select(
            func.sum(case((SentimentAnalysis.sentiment_label == "positive", 1), else_=0)),
            func.sum(case((SentimentAnalysis.sentiment_label == "negative", 1), else_=0)),
            func.sum(case((SentimentAnalysis.sentiment_label == "neutral", 1), else_=0)),
            func.count(SentimentAnalysis.id),
        )
        .join(SocialMediaPost, SocialMediaPost.post_id == SentimentAnalysis.post_id)
        .where(SentimentAnalysis.analyzed_at >= since)
    )

    row = (await db.execute(query)).one_or_none()
    positive, negative, neutral, total = row or (0, 0, 0, 0)

    return {
        "timeframe_hours": hours,
        "distribution": {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
        },
        "total": total,
    }


# ========================= WEBSOCKET =========================

class ConnectionManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict):
        for ws in list(self.connections):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


from models.models import async_session_maker

@router.websocket("/ws/sentiment")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    async with async_session_maker() as db:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )

        aggregator = SentimentAggregator(redis_client)

        try:
            await websocket.send_json({"type": "connected"})
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("sentiment_updates")

            async def metrics_loop():
                while True:
                    data = await aggregator.get_distribution(db, hours=24)
                    await manager.broadcast({
                        "type": "metrics",
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    })
                    await asyncio.sleep(30)

            async def updates_loop():
                async for msg in pubsub.listen():
                    if msg["type"] == "message":
                        await manager.broadcast(json.loads(msg["data"]))

            await asyncio.gather(metrics_loop(), updates_loop())

        except WebSocketDisconnect:
            manager.disconnect(websocket)
        finally:
            await redis_client.close()
