# symbol_utils.py

import requests
import os
import json
import re

SYMBOL_MAP_FILE = "symbol_map.json"

# === Hardcoded fallback map (used if API fails or no file exists) ===
FALLBACK_SYMBOL_MAP = {
    "BTC": "BTCUSDT", "BITCOIN": "BTCUSDT",
    "ETH": "ETHUSDT", "ETHEREUM": "ETHUSDT",
    "SOL": "SOLUSDT", "BNB": "BNBUSDT",
    "ADA": "ADAUSDT", "DOGE": "DOGEUSDT",
    "XRP": "XRPUSDT", "AVAX": "AVAXUSDT",
    "DOT": "DOTUSDT", "MATIC": "MATICUSDT",
    "LTC": "LTCUSDT", "LINK": "LINKUSDT",
    "UNI": "UNIUSDT", "SHIB": "SHIBUSDT",
    "PEPE": "PEPEUSDT", "ARB": "ARBUSDT",
    "OP": "OPUSDT", "APT": "APTUSDT",
    "SUI": "SUIUSDT", "RNDR": "RNDRUSDT",
    "FET": "FETUSDT", "INJ": "INJUSDT",
    "NEAR": "NEARUSDT", "GRT": "GRTUSDT",
    "IMX": "IMXUSDT", "FIL": "FILUSDT",
    "STX": "STXUSDT", "TON": "TONUSDT",
}

def fetch_binance_symbols():
    try:
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        response = requests.get(url, timeout=10)
        symbols = response.json().get("symbols", [])

        symbol_map = {}
        for s in symbols:
            symbol = s["symbol"]
            if symbol.endswith("USDT"):
                base = re.sub(r'[^A-Z]', '', symbol.replace("USDT", ""))
                symbol_map[base] = symbol

        with open(SYMBOL_MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(symbol_map, f, indent=2)

        print("✅ Symbol map refreshed from Binance.")
        return symbol_map

    except Exception as e:
        print("⚠️ Failed to fetch Binance symbols:", e)
        return FALLBACK_SYMBOL_MAP


def load_symbol_map():
    if os.path.exists(SYMBOL_MAP_FILE):
        try:
            with open(SYMBOL_MAP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return FALLBACK_SYMBOL_MAP


def get_symbol_for_title(title):
    title = title.upper()
    symbol_map = load_symbol_map()

    for keyword, symbol in symbol_map.items():
        if keyword in title:
            return symbol

    return None