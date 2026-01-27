# liquidation_map.py

import websocket
import json
import threading
from datetime import datetime, timedelta
from collections import defaultdict

PRICE_BUCKET = 100   # Group by $100 zones
DATA_FILE = "liquidation_summary.txt"
MAX_DURATION_MINUTES = 60  # Rolling 1 hour

# Store: {price_bin: [timestamps]}
liquidation_buckets = defaultdict(list)

def get_bucket(price):
    """Round price to nearest 100"""
    return round(price / PRICE_BUCKET) * PRICE_BUCKET

def prune_old_data():
    """Keep only last 1h data"""
    cutoff = datetime.utcnow() - timedelta(minutes=MAX_DURATION_MINUTES)
    for bucket in list(liquidation_buckets.keys()):
        liquidation_buckets[bucket] = [t for t in liquidation_buckets[bucket] if t > cutoff]
        if not liquidation_buckets[bucket]:
            del liquidation_buckets[bucket]

def generate_summary():
    """Write liquidation summary to text file"""
    prune_old_data()
    sorted_bins = sorted(liquidation_buckets.items(), key=lambda x: x[0], reverse=True)

    lines = ["🔥 LIQUIDATION HEATMAP (Last 1h)"]
    for price_bin, times in sorted_bins:
        count = len(times)
        bar = "█" * min(count, 5) + " ░" * max(0, 5 - count)
        risk = " (High)" if count >= 5 else " (Medium)" if count >= 3 else " (Low)"
        lines.append(f"${price_bin:,.0f}: {bar}{risk}")

    with open(DATA_FILE, "w") as f:
        f.write("\n".join(lines))

def on_message(ws, message):
    try:
        data = json.loads(message)
        price = float(data["o"]["p"])
        price_bin = get_bucket(price)
        liquidation_buckets[price_bin].append(datetime.utcnow())
        generate_summary()
    except Exception as e:
        print("Error parsing message:", e)

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed")

def run_websocket():
    ws_url = "wss://fstream.binance.com/ws/btcusdt@forceOrder"
    ws = websocket.WebSocketApp(ws_url, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.run_forever()

# === Summary loader for daily_summary.py ===
def load_liquidation_summary():
    try:
        with open("liquidation_summary.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "No liquidation data available."

if __name__ == "__main__":
    print("🔌 Listening to Binance liquidation stream...")
    threading.Thread(target=run_websocket).start()