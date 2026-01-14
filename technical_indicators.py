# technical_indicators.py

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

BINANCE_OHLCV_URL = "https://fapi.binance.com/fapi/v1/klines"

def fetch_ohlcv(symbol: str, interval="5m", limit=50):
    try:
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        response = requests.get(BINANCE_OHLCV_URL, params=params)
        data = response.json()

        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "_", "_", "_", "_", "_", "_"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        return df
    except Exception as e:
        print(f"❌ Failed to fetch OHLCV for {symbol}: {e}")
        return None

def compute_rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1] if not rsi.empty else None

def compute_ma_crossover(df, short=20, long=50):
    ma_short = df["close"].rolling(window=short).mean().iloc[-1]
    ma_long = df["close"].rolling(window=long).mean().iloc[-1]

    if ma_short > ma_long:
        return "Bullish"
    elif ma_short < ma_long:
        return "Bearish"
    else:
        return "Neutral"

def compute_volume_spike(df, period=20):
    recent_volume = df["volume"].iloc[-1]
    avg_volume = df["volume"].rolling(window=period).mean().iloc[-1]

    if avg_volume == 0:
        return "Unknown"

    ratio = (recent_volume / avg_volume) * 100
    level = "Low"
    if ratio > 180:
        level = "High"
    elif ratio > 130:
        level = "Medium"

    return f"+{ratio:.0f}% vs avg ({level})"

def get_technical_indicators(symbol: str):
    df = fetch_ohlcv(symbol)
    if df is None or len(df) < 50:
        return None  # Not enough data

    # === RSI ===
    rsi_series = df["close"].diff().clip(lower=0).rolling(window=14).mean() / \
                 df["close"].diff().clip(upper=0).abs().rolling(window=14).mean()
    rsi_series = 100 - (100 / (1 + rsi_series))

    rsi_now = rsi_series.iloc[-1]
    rsi_prev = rsi_series.iloc[-2]
    rsi_trend = "Rising" if rsi_now > rsi_prev else "Falling"

    rsi_label = "Oversold" if rsi_now < 30 else "Overbought" if rsi_now > 70 else "Neutral"

    # === MA Crossover ===
    ma_short_period = 20
    ma_long_period = 50

    ma_short = df["close"].rolling(window=ma_short_period).mean().iloc[-1]
    ma_long = df["close"].rolling(window=ma_long_period).mean().iloc[-1]

    if ma_short > ma_long:
        ma_cross = f"{ma_short_period} > {ma_long_period} (Bullish)"
    elif ma_short < ma_long:
        ma_cross = f"{ma_short_period} < {ma_long_period} (Bearish)"
    else:
        ma_cross = f"{ma_short_period} = {ma_long_period} (Neutral)"

    # === Volume Spike ===
    recent_volume = df["volume"].iloc[-1]
    avg_volume = df["volume"].rolling(window=20).mean().iloc[-1]
    if avg_volume == 0:
        volume_spike = "Unknown"
    else:
        ratio = (recent_volume / avg_volume) * 100
        level = "Low"
        if ratio > 180:
            level = "High"
        elif ratio > 130:
            level = "Medium"
        volume_spike = f"+{ratio:.0f}% vs avg ({level})"

    return {
        "rsi": round(rsi_now, 1),
        "rsi_label": rsi_label,
        "rsi_trend": rsi_trend,
        "ma_crossover": ma_cross,
        "volume_spike": volume_spike
    }

def get_market_change_summary():
    symbols = ["BTCUSDT", "ETHUSDT"]
    interval = "1m"
    limit = 61  # 1 hour + current

    summary = []
    for symbol in symbols:
        try:
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            res = requests.get("https://fapi.binance.com/fapi/v1/klines", params=params)
            data = res.json()
            if len(data) < 2:
                continue

            price_now = float(data[-1][4])  # close price
            price_1h_ago = float(data[0][4])

            pct_change = ((price_now - price_1h_ago) / price_1h_ago) * 100
            label = f"{symbol.replace('USDT','')}: {pct_change:+.1f}%"
            summary.append(label)

        except Exception as e:
            print(f"❌ Error fetching 1h price change for {symbol}: {e}")

    return ", ".join(summary) if summary else "Unavailable"