from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import httpx
from transformers import pipeline


class SentimentAnalyzer:
    """
    Unified interface for sentiment analysis using multiple model backends
    """

    _sentiment_pipeline = None
    _emotion_pipeline = None

    def __init__(self, model_type: str = "local", model_name: Optional[str] = None) -> None:
        """
        Initialize analyzer with specified backend.

        Args:
            model_type: 'local' for Hugging Face or 'external' for LLM API
            model_name: Specific model to use (uses env var if None)
        """
        self.model_type = model_type
        self.model_name = model_name

        if self.model_type == "local":
            # Sentiment model
            if SentimentAnalyzer._sentiment_pipeline is None:
                base_model = model_name or os.getenv(
                    "HUGGINGFACE_MODEL", "distilbert-base-uncased-finetuned-sst-2-english"
                )
                SentimentAnalyzer._sentiment_pipeline = pipeline(
                    "sentiment-analysis", model=base_model
                )

            # Emotion model
            if SentimentAnalyzer._emotion_pipeline is None:
                emo_model = os.getenv(
                    "EMOTION_MODEL", "j-hartmann/emotion-english-distilroberta-base"
                )
                SentimentAnalyzer._emotion_pipeline = pipeline(
                    "text-classification", model=emo_model, return_all_scores=True
                )

            self._client = None
        else:
            # External LLM backend
            self._client = httpx.AsyncClient(timeout=15.0)
            self.api_key = os.getenv("EXTERNAL_LLM_API_KEY")
            self.api_model = model_name or os.getenv("EXTERNAL_LLM_MODEL", "llama-3.1-8b-instant")
            self.provider = os.getenv("EXTERNAL_LLM_PROVIDER", "groq")

    def _normalize_sentiment_label(self, label: str) -> str:
        label = label.lower()
        if "pos" in label:
            return "positive"
        if "neg" in label:
            return "negative"
        return "neutral"

    def _clip_confidence(self, score: float) -> float:
        return max(0.0, min(float(score), 1.0))

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of input text.

        Returns:
            {
                'sentiment_label': 'positive' | 'negative' | 'neutral',
                'confidence_score': float between 0.0 and 1.0,
                'model_name': str
            }
        """
        if text is None or not text.strip():
            raise ValueError("Text for sentiment analysis must not be empty")

        truncated = text[:512]

        if self.model_type == "local":
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, SentimentAnalyzer._sentiment_pipeline, truncated
            )
            if isinstance(result, list):
                result = result[0]

            label = self._normalize_sentiment_label(result["label"])
            score = self._clip_confidence(result["score"])
            model_name = SentimentAnalyzer._sentiment_pipeline.model.name_or_path

            return {
                "sentiment_label": label,
                "confidence_score": score,
                "model_name": model_name,
            }

        # External LLM backend
        if not getattr(self, "api_key", None):
            # No key configured: return neutral but valid structure
            return {
                "sentiment_label": "neutral",
                "confidence_score": 0.5,
                "model_name": getattr(self, "api_model", "external-llm"),
            }

        prompt = (
            "You are a strict sentiment classifier.\n"
            "Classify the sentiment of the following text as 'positive', 'negative', or 'neutral'.\n"
            "Respond ONLY with JSON:\n"
            '{"sentiment_label": "positive|negative|neutral", "confidence_score": 0.0-1.0}\n\n'
            f"Text: {truncated}"
        )

        payload = {
            "model": self.api_model,
            "messages": [
                {"role": "system", "content": "You are a JSON-only sentiment classifier."},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = os.getenv("EXTERNAL_LLM_URL", "https://api.groq.com/openai/v1/chat/completions")

        resp = await self._client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        try:
            parsed = json.loads(content)
            label = self._normalize_sentiment_label(parsed.get("sentiment_label", "neutral"))
            score = self._clip_confidence(float(parsed.get("confidence_score", 0.5)))
        except Exception:
            label = "neutral"
            score = 0.5

        return {
            "sentiment_label": label,
            "confidence_score": score,
            "model_name": self.api_model,
        }

    async def analyze_emotion(self, text: str) -> Dict[str, Any]:
        """
        Detect primary emotion in text.

        Returns:
            {
                'emotion': 'joy' | 'sadness' | 'anger' | 'fear' | 'surprise' | 'neutral',
                'confidence_score': float between 0.0 and 1.0,
                'model_name': str
            }
        """
        if text is None or not text.strip():
            raise ValueError("Text for emotion analysis must not be empty")

        truncated = text[:512]

        # Very short text -> neutral
        if len(truncated) < 10:
            model_name = (
                SentimentAnalyzer._emotion_pipeline.model.name_or_path
                if self.model_type == "local"
                else getattr(self, "api_model", "external-llm")
            )
            return {
                "emotion": "neutral",
                "confidence_score": 1.0,
                "model_name": model_name,
            }

        if self.model_type == "local":
            loop = asyncio.get_running_loop()
            scores_list = await loop.run_in_executor(
                None, SentimentAnalyzer._emotion_pipeline, truncated
            )
            if scores_list and isinstance(scores_list, list):
                scores = scores_list[0]
            else:
                scores = scores_list

            best_label = None
            best_score = -1.0
            for item in scores:
                label = item["label"].lower()
                score = float(item["score"])
                if score > best_score:
                    best_score = score
                    best_label = label

            mapping = {
                "joy": "joy",
                "happiness": "joy",
                "sadness": "sadness",
                "anger": "anger",
                "fear": "fear",
                "surprise": "surprise",
                "neutral": "neutral",
            }
            emotion = mapping.get(best_label, "neutral")
            score = self._clip_confidence(best_score)
            model_name = SentimentAnalyzer._emotion_pipeline.model.name_or_path

            return {
                "emotion": emotion,
                "confidence_score": score,
                "model_name": model_name,
            }

        # External LLM backend
        if not getattr(self, "api_key", None):
            return {
                "emotion": "neutral",
                "confidence_score": 0.5,
                "model_name": getattr(self, "api_model", "external-llm"),
            }

        prompt = (
            "You are a strict emotion classifier.\n"
            "Classify the PRIMARY emotion of the following text as one of:\n"
            "'joy', 'sadness', 'anger', 'fear', 'surprise', 'neutral'.\n"
            "Respond ONLY with JSON:\n"
            '{"emotion": "joy|sadness|anger|fear|surprise|neutral", "confidence_score": 0.0-1.0}\n\n'
            f"Text: {truncated}"
        )

        payload = {
            "model": self.api_model,
            "messages": [
                {"role": "system", "content": "You are a JSON-only emotion classifier."},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = os.getenv("EXTERNAL_LLM_URL", "https://api.groq.com/openai/v1/chat/completions")

        resp = await self._client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

        try:
            parsed = json.loads(content)
            emotion = str(parsed.get("emotion", "neutral")).lower()
            if emotion not in {"joy", "sadness", "anger", "fear", "surprise", "neutral"}:
                emotion = "neutral"
            score = self._clip_confidence(float(parsed.get("confidence_score", 0.5)))
        except Exception:
            emotion = "neutral"
            score = 0.5

        return {
            "emotion": emotion,
            "confidence_score": score,
            "model_name": self.api_model,
        }

    async def batch_analyze(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze multiple texts efficiently.

        Returns list of sentiment results in same order as input.
        """
        if not texts:
            return []

        results: List[Dict[str, Any]] = []

        if self.model_type == "local":
            loop = asyncio.get_running_loop()
            batch = await loop.run_in_executor(
                None,
                SentimentAnalyzer._sentiment_pipeline,
                [t[:512] if t is not None else "" for t in texts],
            )
            for item in batch:
                label = self._normalize_sentiment_label(item["label"])
                score = self._clip_confidence(item["score"])
                results.append(
                    {
                        "sentiment_label": label,
                        "confidence_score": score,
                        "model_name": SentimentAnalyzer._sentiment_pipeline.model.name_or_path,
                    }
                )
        else:
            async def one(text: str) -> Dict[str, Any]:
                try:
                    return await self.analyze_sentiment(text)
                except Exception:
                    return {
                        "sentiment_label": "neutral",
                        "confidence_score": 0.0,
                        "model_name": getattr(self, "api_model", "external-llm"),
                        "error": True,
                    }

            results = await asyncio.gather(*[one(t) for t in texts])

        return results
