from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from models.models import SocialMediaPost, SentimentAnalysis
from datetime import datetime


async def save_post_and_analysis(
    db_session,
    post_data: dict,
    sentiment_result: dict,
    emotion_result: dict
) -> tuple[int, int]:
    """
    Save post and analysis results to PostgreSQL using async SQLAlchemy
    """

    try:
        # 1️⃣ Check if post already exists
        result = await db_session.execute(
            select(SocialMediaPost).where(
                SocialMediaPost.post_id == post_data["post_id"]
            )
        )
        post = result.scalar_one_or_none()

        # 2️⃣ Insert new post or update existing
        if post is None:
            post = SocialMediaPost(
                post_id=post_data["post_id"],
                source=post_data["source"],
                content=post_data["content"],
                author=post_data["author"],
                created_at=post_data["created_at"],
                ingested_at=datetime.utcnow(),
            )
            db_session.add(post)
            await db_session.flush()  # ensure post.id is available
        else:
            post.ingested_at = datetime.utcnow()
            await db_session.flush()

        # 3️⃣ Insert sentiment analysis linked to this post
        analysis = SentimentAnalysis(
            post_id=post.id,
            sentiment_label=sentiment_result["sentiment_label"],
            sentiment_score=sentiment_result["confidence_score"],
            emotion=emotion_result["emotion"],
            emotion_score=emotion_result["confidence_score"],
            model_name=sentiment_result["model_name"],
        )
        db_session.add(analysis)

        # 4️⃣ Commit transaction
        await db_session.commit()

        # 5️⃣ Return database IDs
        return post.id, analysis.id

    except SQLAlchemyError as e:
        # Rollback on error
        await db_session.rollback()
        raise e
