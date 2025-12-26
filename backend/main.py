import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from backend.models import init_models
from backend.api.routes import router as api_router

settings = get_settings()

app = FastAPI(title="Sentiment Platform API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{settings.frontend_port}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    await init_models()


@app.get("/")
async def root() -> dict:
    return {"message": "Sentiment Platform API"}


app.include_router(api_router)
