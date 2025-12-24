import pytest
from httpx import AsyncClient
from backend.main import app


@pytest.mark.asyncio
async def test_health_check():
    """
    Test health endpoint
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health")

    assert response.status_code in (200, 503)
    assert "status" in response.json()


@pytest.mark.asyncio
async def test_get_posts_empty():
    """
    Test posts endpoint with empty DB
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/posts")

    assert response.status_code == 200
    data = response.json()
    assert "posts" in data
    assert isinstance(data["posts"], list)


@pytest.mark.asyncio
async def test_sentiment_distribution():
    """
    Test sentiment distribution API
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/sentiment/distribution")

    assert response.status_code == 200
    body = response.json()
    assert "distribution" in body
    assert "total" in body
