import pytest
from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_endpoint_returns_status():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "services" in body
    assert "stats" in body


def test_get_posts_empty_list_initially():
    response = client.get("/api/posts")
    assert response.status_code == 200
    body = response.json()
    assert "posts" in body
    assert isinstance(body["posts"], list)
    assert "total" in body
    assert "offset" in body
    assert "filters" in body


@pytest.mark.parametrize("period", ["minute", "hour", "day"])
def test_sentiment_aggregate_endpoint(period: str):
    response = client.get(f"/api/sentiment/aggregate?period={period}")
    assert response.status_code == 200
    body = response.json()
    assert body["period"] == period
    assert "data" in body
    assert "summary" in body


def test_sentiment_distribution_endpoint_default_hours():
    response = client.get("/api/sentiment/distribution")
    assert response.status_code == 200
    body = response.json()
    assert "timeframe_hours" in body
    assert "distribution" in body
    assert "percentages" in body["distribution"]
