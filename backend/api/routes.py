from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import aioredis
import json
import asyncio

from backend.models.models import (
    async_session,
    SocialMediaPost,
    SentimentAnalysis
)

router = APIRouter()

# Initialize async Redis client
redis = aioredis.from_url("redis://redis:6379", decode_responses=True)

connected_clients = set()


# -----------------------------
# REST APIs
# -----------------------------

@router.get("/api/health")
async def health_check():
    db_status = "connected"
    redis_status = "connected"

    try:
        async with async_session() as session:
            await session.execute(select(1))
    except Exception:
        db_status = "disconnected"

    try:
        await redis.ping()
    except Exception:
        redis_status = "disconnected"

    total_posts = total_analyses = recent_posts_1h = 0
    try:
        async with async_session() as session:
            total_posts = await session.scalar(select(func.count()).select_from(SocialMediaPost))
            total_analyses = await session.scalar(select(func.count()).select_from(SentimentAnalysis))

            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_posts_1h = await session.scalar(
                select(func.count()).select_from(SocialMediaPost).filter(SocialMediaPost.created_at >= one_hour_ago)
            )
    except Exception:
        pass

    healthy = db_status == "connected" and redis_status == "connected"

    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "healthy" if healthy else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {
                "database": db_status,
                "redis": redis_status
            },
            "stats": {
                "total_posts": total_posts,
                "total_analyses": total_analyses,
                "recent_posts_1h": recent_posts_1h
            }
        }
    )


@router.get("/api/posts")
async def get_posts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    source: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    async with async_session() as session:
        query = select(SocialMediaPost, SentimentAnalysis).join(
            SentimentAnalysis, SocialMediaPost.id == SentimentAnalysis.post_id
        )

        if source:
            query = query.filter(SocialMediaPost.source == source)
        if sentiment:
            query = query.filter(SentimentAnalysis.sentiment_label == sentiment)
        if start_date:
            query = query.filter(SocialMediaPost.created_at >= start_date)
        if end_date:
            query = query.filter(SocialMediaPost.created_at <= end_date)

        total = await session.scalar(select(func.count()).select_from(query.subquery()))

        query = query.order_by(SocialMediaPost.created_at.desc()).offset(offset).limit(limit)
        rows = (await session.execute(query)).all()

        posts = [
            {
                "post_id": post.post_id,
                "source": post.source,
                "content": post.content,
                "author": post.author,
                "created_at": post.created_at.isoformat(),
                "sentiment": {
                    "label": analysis.sentiment_label,
                    "confidence": analysis.sentiment_score,
                    "emotion": analysis.emotion,
                    "model_name": analysis.model_name
                }
            }
            for post, analysis in rows
        ]

        return {
            "posts": posts,
            "total": total,
            "limit": limit,
            "offset": offset,
            "filters": {
                "source": source,
                "sentiment": sentiment,
                "start_date": start_date,
                "end_date": end_date
            }
        }


@router.get("/api/sentiment/aggregate")
async def get_sentiment_aggregate(
    period: str = Query(..., regex="^(minute|hour|day)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    source: Optional[str] = Query(None)
):
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        start_date = end_date - timedelta(hours=24)

    cache_key = f"aggregate:{period}:{start_date.isoformat()}:{end_date.isoformat()}:{source}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    async with async_session() as session:
        time_bucket = func.date_trunc(period, SocialMediaPost.created_at)
        query = select(
            time_bucket.label("bucket"),
            SentimentAnalysis.sentiment_label,
            func.count().label("count"),
            func.avg(SentimentAnalysis.sentiment_score).label("avg_conf")
        ).join(SentimentAnalysis, SocialMediaPost.id == SentimentAnalysis.post_id).filter(
            SocialMediaPost.created_at.between(start_date, end_date)
        )

        if source:
            query = query.filter(SocialMediaPost.source == source)

        query = query.group_by(time_bucket, SentimentAnalysis.sentiment_label).order_by(time_bucket)
        rows = (await session.execute(query)).all()

    buckets = {}
    summary = {"positive": 0, "negative": 0, "neutral": 0}

    for bucket, label, count, avg_conf in rows:
        ts = bucket.isoformat()
        if ts not in buckets:
            buckets[ts] = {"positive_count": 0, "negative_count": 0, "neutral_count": 0, "conf_sum": 0, "total": 0}
        buckets[ts][f"{label}_count"] += count
        buckets[ts]["conf_sum"] += avg_conf * count
        buckets[ts]["total"] += count
        summary[label] += count

    data = []
    for ts, v in buckets.items():
        total = v["total"]
        data.append({
            "timestamp": ts,
            "positive_count": v["positive_count"],
            "negative_count": v["negative_count"],
            "neutral_count": v["neutral_count"],
            "total_count": total,
            "positive_percentage": (v["positive_count"] / total) * 100 if total else 0,
            "negative_percentage": (v["negative_count"] / total) * 100 if total else 0,
            "neutral_percentage": (v["neutral_count"] / total) * 100 if total else 0,
            "average_confidence": v["conf_sum"] / total if total else 0
        })

    result = {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "data": data,
        "summary": {
            "total_posts": sum(summary.values()),
            "positive_total": summary["positive"],
            "negative_total": summary["negative"],
            "neutral_total": summary["neutral"]
        }
    }

    await redis.set(cache_key, json.dumps(result), ex=60)
    return result


@router.get("/api/sentiment/distribution")
async def get_sentiment_distribution(
    hours: int = Query(24, ge=1, le=168),
    source: Optional[str] = Query(None)
):
    cache_key = f"distribution:{hours}:{source}"
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        data["cached"] = True
        return data

    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    async with async_session() as session:
        query = select(
            SentimentAnalysis.sentiment_label,
            SentimentAnalysis.emotion,
            func.count()
        ).join(SocialMediaPost, SocialMediaPost.id == SentimentAnalysis.post_id).filter(
            SocialMediaPost.created_at >= since
        )
        if source:
            query = query.filter(SocialMediaPost.source == source)
        query = query.group_by(SentimentAnalysis.sentiment_label, SentimentAnalysis.emotion)
        rows = (await session.execute(query)).all()

    distribution = {"positive": 0, "negative": 0, "neutral": 0}
    emotions = {}
    for label, emotion, count in rows:
        distribution[label] += count
        emotions[emotion] = emotions.get(emotion, 0) + count

    total = sum(distribution.values())
    top_emotions = dict(sorted(emotions.items(), key=lambda x: x[1], reverse=True)[:5])

    result = {
        "timeframe_hours": hours,
        "source": source,
        "distribution": distribution,
        "total": total,
        "percentages": {k: (v / total) * 100 if total else 0 for k, v in distribution.items()},
        "top_emotions": top_emotions,
        "cached": False,
        "cached_at": datetime.now(timezone.utc).isoformat()
    }

    await redis.set(cache_key, json.dumps(result), ex=60)
    return result


# -----------------------------
# WebSocket Endpoint
# -----------------------------

@router.websocket("/ws/sentiment")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)

    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to sentiment stream",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        pubsub = redis.pubsub()
        await pubsub.subscribe("new_sentiment_post")

        last_metrics_sent = datetime.now(timezone.utc)

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if message and "data" in message:
                data = json.loads(message["data"])
                await broadcast({
                    "type": "new_post",
                    "data": data
                })

            now = datetime.now(timezone.utc)
            if (now - last_metrics_sent).seconds >= 30:
                metrics = await calculate_metrics()
                await broadcast({
                    "type": "metrics_update",
                    "data": metrics,
                    "timestamp": now.isoformat()
                })
                last_metrics_sent = now

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    finally:
        await pubsub.unsubscribe("new_sentiment_post")
        await pubsub.close()


# -----------------------------
# Helper Functions
# -----------------------------

async def broadcast(message: dict):
    dead_clients = set()
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            dead_clients.add(client)
    for dc in dead_clients:
        connected_clients.remove(dc)


async def calculate_metrics():
    now = datetime.now(timezone.utc)

    async def count_since(hours: float):
        since = now - timedelta(hours=hours)
        async with async_session() as session:
            rows = await session.execute(
                select(SentimentAnalysis.sentiment_label, func.count()).join(
                    SocialMediaPost, SocialMediaPost.id == SentimentAnalysis.post_id
                ).filter(SocialMediaPost.created_at >= since).group_by(SentimentAnalysis.sentiment_label)
            )
            counts = {"positive": 0, "negative": 0, "neutral": 0}
            for label, count in rows.all():
                counts[label] = count
            counts["total"] = sum(counts.values())
            return counts

    return {
        "last_minute": await count_since(1/60),
        "last_hour": await count_since(1),
        "last_24_hours": await count_since(24)
    }
