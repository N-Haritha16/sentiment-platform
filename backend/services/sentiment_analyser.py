import os
import asyncio
from typing import List
from transformers import pipeline
import httpx


class SentimentAnalyzer:
    """
    Unified interface for sentiment analysis using local HuggingFace models
    or an external LLM API.
    """

    _sentiment_pipeline = None
    _emotion_pipeline = None

    def __init__(self, model_type: str = "local", model_name: str = None):
        self.model_type = model_type

        if self.model_type == "local":
            self.sentiment_model_name = (
                model_name
                or os.getenv(
                    "HUGGINGFACE_MODEL",
                    "distilbert-base-uncased-finetuned-sst-2-english",
                )
            )
            self.emotion_model_name = os.getenv(
                "EMOTION_MODEL",
                "j-hartmann/emotion-english-distilroberta-base",
            )

            if SentimentAnalyzer._sentiment_pipeline is None:
                SentimentAnalyzer._sentiment_pipeline = pipeline(
                    "text-classification",
                    model=self.sentiment_model_name,
                    truncation=True,
                )

            if SentimentAnalyzer._emotion_pipeline is None:
                SentimentAnalyzer._emotion_pipeline = pipeline(
                    "text-classification",
                    model=self.emotion_model_name,
                    top_k=None,
                )

        elif self.model_type == "external":
            self.api_key = os.getenv("EXTERNAL_LLM_API_KEY")
            self.model_name = os.getenv("EXTERNAL_LLM_MODEL")

            if not self.api_key:
                raise ValueError("EXTERNAL_LLM_API_KEY is not set")

            self.client = httpx.AsyncClient(timeout=15)

        else:
            raise ValueError("model_type must be 'local' or 'external'")

    # --------------------------------------------------

    async def analyze_sentiment(self, text: str) -> dict:
        if not text or not text.strip():
            return {
                "sentiment_label": "neutral",
                "confidence_score": 0.0,
                "model_name": "none",
            }

        if self.model_type == "local":
            result = SentimentAnalyzer._sentiment_pipeline(text)[0]

            label = result["label"].lower()
            score = float(result["score"])

            if label not in {"positive", "negative"}:
                label = "neutral"

            return {
                "sentiment_label": label,
                "confidence_score": round(score, 4),
                "model_name": self.sentiment_model_name,
            }

        # External LLM
        prompt = (
            "Classify the sentiment of the following text as "
            "positive, negative, or neutral and return JSON only.\n\n"
            f"Text: {text}"
        )

        response = await self._call_external_llm(prompt)

        return {
            "sentiment_label": response.get("sentiment", "neutral"),
            "confidence_score": float(response.get("confidence", 0.5)),
            "model_name": self.model_name,
        }

    # --------------------------------------------------

    async def analyze_emotion(self, text: str) -> dict:
        if not text:
            raise ValueError("Text cannot be empty")

        if len(text.strip()) < 10:
            return {
                "emotion": "neutral",
                "confidence_score": 0.0,
                "model_name": "rule-based",
            }

        if self.model_type == "local":
            results = SentimentAnalyzer._emotion_pipeline(text)[0]
            top_emotion = max(results, key=lambda r: r["score"])

            return {
                "emotion": top_emotion["label"].lower(),
                "confidence_score": round(float(top_emotion["score"]), 4),
                "model_name": self.emotion_model_name,
            }

        prompt = (
            "Detect the strongest emotion in the following text "
            "from: joy, sadness, anger, fear, surprise, neutral.\n"
            "Return JSON only.\n\n"
            f"Text: {text}"
        )

        response = await self._call_external_llm(prompt)

        return {
            "emotion": response.get("emotion", "neutral"),
            "confidence_score": float(response.get("confidence", 0.5)),
            "model_name": self.model_name,
        }

    # --------------------------------------------------

    async def batch_analyze(self, texts: List[str]) -> List[dict]:
        if not texts:
            return []

        if self.model_type == "local":
            results = []
            for text in texts:
                try:
                    result = await self.analyze_sentiment(text)
                    results.append(result)
                except Exception as exc:
                    results.append({"error": str(exc)})
            return results

        tasks = [self.analyze_sentiment(text) for text in texts]
        return await asyncio.gather(*tasks, return_exceptions=True)

    # --------------------------------------------------

    async def _call_external_llm(self, prompt: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = await self.client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return eval(content)
        except Exception:
            return {"sentiment": "neutral", "confidence": 0.5}
