# gpt_cache.py

import json
import os

CACHE_FILE = "gpt_cache.json"


def _load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def _save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def get_cached_result(news_id):
    cache = _load_cache()
    return cache.get(news_id)


def save_cached_result(news_id, data):
    """
    data structure example:
    {
        "is_hard_news": true,
        "signal": "BUY",
        "label": "🟢 Bullish",
        "confidence": 82,
        "reason": "ETF inflows increased",
        "ticker": "ETHUSDT",
        "ticker_source": "symbol_map" | "gpt"
    }
    """
    cache = _load_cache()
    cache[news_id] = data
    _save_cache(cache)