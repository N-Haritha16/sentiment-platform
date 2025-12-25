from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    database_url: str

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_stream_name: str = "social_posts_stream"
    redis_consumer_group: str = "sentiment_workers"
    redis_cache_prefix: str = "sentiment_cache"

    huggingface_model: str = "distilbert-base-uncased-finetuned-sst-2-english"
    emotion_model: str = "j-hartmann/emotion-english-distilroberta-base"
    external_llm_provider: str = "groq"
    external_llm_api_key: str
    external_llm_model: str = "llama-3.1-8b-instant"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_port: int = 3000
    log_level: str = "INFO"

    alert_negative_ratio_threshold: float = 2.0
    alert_window_minutes: int = 5
    alert_min_posts: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
