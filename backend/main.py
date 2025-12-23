from fastapi import FastAPI
from datetime import datetime
from transformers import pipeline

app = FastAPI()
sentiment_model = pipeline("sentiment-analysis", return_all_scores=True)

@app.post("/analyze")
async def analyze_text(payload: dict):
    text = payload.get("text", "")

    results = sentiment_model(text)[0]
    scores = {r["label"].lower(): round(r["score"], 2) for r in results}

    sentiment = max(scores, key=scores.get)

    return {
        "sentiment": sentiment,
        "scores": scores,
        "timestamp": datetime.utcnow().isoformat()
    }
