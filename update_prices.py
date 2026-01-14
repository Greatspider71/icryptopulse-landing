# update_prices.py

import csv
import os
import shutil
import time
from datetime import datetime
import requests

from gpt_cache import get_cached_result, save_cached_result
from confidence import calibrate_confidence

# === CONFIG ===
PENDING_FILE = "pending_prices.csv"
SIGNAL_LOG = "signals_log.csv"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/ticker/price"
LOG_FILE = "logs/update_prices.log"

os.makedirs("logs", exist_ok=True)

def log(msg):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_msg + "\n")

def get_futures_price(symbol, retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(BINANCE_FUTURES_URL, params={"symbol": symbol}, timeout=10)
            data = response.json()
            return float(data["price"])
        except Exception as e:
            log(f"❌ Error fetching price for {symbol} (try {attempt+1}): {e}")
            time.sleep(1)
    return None

def read_pending_entries():
    if not os.path.exists(PENDING_FILE):
        return []

    with open(PENDING_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def write_pending_entries(entries):
    with open(PENDING_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Timestamp", "Asset", "Price_at_Signal", "Check_After"])
        writer.writeheader()
        writer.writerows(entries)

def backup_signal_log():
    if os.path.exists(SIGNAL_LOG):
        backup_path = SIGNAL_LOG.replace(".csv", f"_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv")
        shutil.copy(SIGNAL_LOG, backup_path)
        log(f"🗂️ Backed up signal log to {backup_path}")

def update_signals_log(asset, timestamp, price_after_3h):
    updated_rows = []
    found = False

    with open(SIGNAL_LOG, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        if (row["Asset"] == asset and row["Timestamp"] == timestamp and not row["Price_after_3h"]):
            try:
                price_at_signal = float(row["Price_at_Signal"])
                change_percent = ((price_after_3h - price_at_signal) / price_at_signal) * 100

                news_id = row["URL"].strip()
                cached = get_cached_result(news_id)

                if cached and cached.get("confidence") is not None:
                    calibrated = calibrate_confidence(
                        raw_confidence=int(cached["confidence"]),
                        ticker_source=cached.get("ticker_source", "symbol_map"),
                        source_count=1,
                        historical_price_change=change_percent
                    )
                    row["Confidence"] = str(calibrated)
                    cached["confidence"] = calibrated
                    save_cached_result(news_id, cached)
                    log(f"✅ Recalibrated confidence for {news_id}: {calibrated}%")

                row["Price_after_3h"] = str(price_after_3h)
                row["Price_Change_%"] = f"{change_percent:.2f}"
                found = True
            except Exception as e:
                log(f"⚠️ Error computing % change for {asset} at {timestamp}: {e}")

        updated_rows.append(row)

    if found:
        backup_signal_log()

        with open(SIGNAL_LOG, mode='w', newline='', encoding='utf-8') as f:
            fieldnames = list(rows[0].keys()) if rows else row.keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)
        log(f"📈 Updated signal log for {asset} at {timestamp}")
    else:
        # Try debugging mismatch
        matches = [r["Timestamp"] for r in rows if r["Asset"] == asset]
        log(f"⚠️ No matching row found for {asset} at {timestamp}. Available timestamps: {matches}")

def main():
    now = datetime.utcnow()
    pending = read_pending_entries()
    remaining = []

    for entry in pending:
        try:
            check_time = datetime.strptime(entry["Check_After"], "%Y-%m-%d %H:%M:%S")
        except:
            log(f"⚠️ Invalid datetime format in pending entry: {entry}")
            continue

        if now >= check_time:
            symbol = entry["Asset"]
            timestamp = entry["Timestamp"]
            price = get_futures_price(symbol)
            if price:
                update_signals_log(symbol, timestamp, price)
            else:
                log(f"⚠️ Could not fetch price for {symbol}, keeping in pending.")
                remaining.append(entry)
        else:
            remaining.append(entry)

    write_pending_entries(remaining)

if __name__ == "__main__":
    main()