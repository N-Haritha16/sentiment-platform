from backend.models.models import SocialMediaPost, SentimentAnalysis

async def save_post_and_analysis(
    db_session,
    post_data: dict,
    sentiment: dict,
    emotion: dict
):
    post = SocialMediaPost(
        post_id=post_data.get("post_id"),
        source=post_data.get("source", "unknown"),
        content=post_data["content"],
        author=post_data.get("author", "anonymous"),
        created_at=post_data.get("created_at")
    )
    db_session.add(post)
    await db_session.flush()

    analysis = SentimentAnalysis(
        post_id=post.id,
        sentiment_label=sentiment["sentiment_label"],
        sentiment_score=sentiment["confidence_score"],
        emotion=emotion["emotion"],
        emotion_score=emotion["confidence_score"],
        model_name=sentiment["model_name"]
    )
    db_session.add(analysis)
    await db_session.commit()
