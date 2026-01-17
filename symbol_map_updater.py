# symbol_map_updater.py

import requests
import json
import re

BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/exchangeInfo"
OUTPUT_FILE = "symbol_map.py"

def generate_symbol_map():
    try:
        response = requests.get(BINANCE_FUTURES_URL, timeout=10)
        data = response.json()
        symbols = data.get("symbols", [])

        symbol_map = {}

        for s in symbols:
            symbol = s["symbol"]
            base = s["baseAsset"].upper()
            quote = s["quoteAsset"].upper()

            # Only include USDT perpetual pairs
            if quote != "USDT":
                continue
            if not s.get("contractType") == "PERPETUAL":
                continue

            # Only allow base symbols that are 3+ letters to reduce false positives
            if base not in symbol_map and len(base) >= 3:
                symbol_map[base] = symbol

            # === Aliases for special Binance contracts ===

            # SHIB is traded as 1000SHIBUSDT on Binance
            if base == "1000SHIB":
                symbol_map["SHIB"] = symbol
                symbol_map["SHIBA"] = symbol
                symbol_map["SHIBA INU"] = symbol

            # PEPE is traded as 1000PEPEUSDT
            if base == "1000PEPE":
                symbol_map["PEPE"] = symbol
                symbol_map["PEPECOIN"] = symbol

            # BONK is traded as 1000BONKUSDT
            if base == "1000BONK":
                symbol_map["BONK"] = symbol

            # FLOKI is traded as 1000FLOKIUSDT
            if base == "1000FLOKI":
                symbol_map["FLOKI"] = symbol

            # Add simple alias mapping (e.g., BITCOIN → BTCUSDT)
            if base == "BTC":
                symbol_map["BITCOIN"] = symbol
            elif base == "ETH":
                symbol_map["ETHEREUM"] = symbol
            elif base == "DOGE":
                symbol_map["DOGECOIN"] = symbol
            elif base == "XRP":
                symbol_map["RIPPLE"] = symbol

        # Write to symbol_map.py
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("# Auto-generated symbol map from Binance Futures\n")
            f.write("symbol_map = ")
            json.dump(symbol_map, f, indent=2, sort_keys=True)

        print(f"✅ symbol_map.py updated with {len(symbol_map)} entries.")

    except Exception as e:
        print(f"❌ Error fetching Binance symbols: {e}")

if __name__ == "__main__":
    generate_symbol_map()