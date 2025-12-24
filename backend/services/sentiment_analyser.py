class SentimentAnalyzer:
    def __init__(self, model_type: str = "local"):
        self.model_type = model_type

    async def analyze_sentiment(self, text: str) -> dict:
        text = text.lower()
        if "good" in text or "happy" in text:
            return {
                "sentiment_label": "positive",
                "confidence_score": 0.9,
                "model_name": "rule-based"
            }
        if "bad" in text or "sad" in text:
            return {
                "sentiment_label": "negative",
                "confidence_score": 0.9,
                "model_name": "rule-based"
            }
        return {
            "sentiment_label": "neutral",
            "confidence_score": 0.6,
            "model_name": "rule-based"
        }

    async def analyze_emotion(self, text: str) -> dict:
        return {
            "emotion": "neutral",
            "confidence_score": 0.6,
            "model_name": "rule-based"
        }
