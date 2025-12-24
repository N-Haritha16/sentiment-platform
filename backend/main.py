from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.models.models import engine, Base

app = FastAPI(
    title="Sentiment Platform API",
    version="1.0.0"
)

# ✅ ADD THIS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # frontend access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(router)
