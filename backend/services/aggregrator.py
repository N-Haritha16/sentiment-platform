from typing import List, Dict
from sqlalchemy.engine import Row


def count_sentiments(rows: List[Row]) -> Dict[str, int]:
    """
    Aggregate sentiment counts from DB rows.

    Expected row format:
    (sentiment_label, count)
    """

    result = {
        "positive": 0,
        "negative": 0,
        "neutral": 0
    }

    for label, count in rows:
        if label in result:
            result[label] += count

    result["total"] = sum(result.values())
    return result
