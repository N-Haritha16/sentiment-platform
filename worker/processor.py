from __future__ import annotations

from typing import Dict, Tuple

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.models import SocialMediaPost, SentimentAnalysis


async def save_post_and_analysis(
    db_session: AsyncSession,
    post_data: Dict,
    sentiment_result: Dict,
    emotion_result: Dict,
) -> Tuple[int, int]:
    """
    Save post and analysis results to database.

    Returns:
        (post_id_pk, analysis_id_pk)
    """
    try:
        # 1. Insert into social_media_posts (or update if exists based on post_id)
        stmt = select(SocialMediaPost).where(SocialMediaPost.post_id == post_data["post_id"])
        result = await db_session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update only ingested_at (and maybe content if you want)
            existing.ingested_at = post_data.get("ingested_at") or existing.ingested_at
            db_post = existing
        else:
            db_post = SocialMediaPost(
                post_id=post_data["post_id"],
                source=post_data["source"],
                content=post_data["content"],
                author=post_data["author"],
                created_at=post_data["created_at"],
            )
            db_session.add(db_post)

        await db_session.flush()  # ensure db_post.id is populated

        # 2. Insert into sentiment_analysis referencing the post
        db_analysis = SentimentAnalysis(
            post_id=db_post.post_id,
            model_name=sentiment_result["model_name"],
            sentiment_label=sentiment_result["sentiment_label"],
            confidence_score=float(sentiment_result["confidence_score"]),
            emotion=emotion_result.get("emotion"),
        )
        db_session.add(db_analysis)

        await db_session.flush()  # populate db_analysis.id

        # 3. Commit transaction
        await db_session.commit()

        # 4. Return both database IDs
        return db_post.id, db_analysis.id

    except SQLAlchemyError as exc:
        # If commit fails, rollback and re-raise
        await db_session.rollback()
        raise exc
