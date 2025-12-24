import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://sentiment:sentiment@db:5432/sentimentdb"
)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_STREAM_NAME = os.getenv("REDIS_STREAM_NAME", "social_media_posts")
REDIS_CONSUMER_GROUP = os.getenv("REDIS_CONSUMER_GROUP", "sentiment_workers")

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

HUGGINGFACE_MODEL = os.getenv(
    "HUGGINGFACE_MODEL",
    "distilbert-base-uncased-finetuned-sst-2-english"
)

EMOTION_MODEL = os.getenv(
    "EMOTION_MODEL",
    "j-hartmann/emotion-english-distilroberta-base"
)

EXTERNAL_LLM_PROVIDER = os.getenv("EXTERNAL_LLM_PROVIDER", "")
EXTERNAL_LLM_API_KEY = os.getenv("EXTERNAL_LLM_API_KEY", "")
EXTERNAL_LLM_MODEL = os.getenv("EXTERNAL_LLM_MODEL", "")

ALERT_NEGATIVE_RATIO_THRESHOLD = float(
    os.getenv("ALERT_NEGATIVE_RATIO_THRESHOLD", 2.0)
)
ALERT_WINDOW_MINUTES = int(os.getenv("ALERT_WINDOW_MINUTES", 5))
ALERT_MIN_POSTS = int(os.getenv("ALERT_MIN_POSTS", 10))
