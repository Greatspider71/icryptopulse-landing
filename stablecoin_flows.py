# stablecoin_flows.py
# Track stablecoin minting as a proxy for exchange inflows (whale indicator)

import json
import requests
import csv
from datetime import datetime, timedelta
import os

MOCK_FILE = "stablecoin_flows.json"
OUTPUT_FILE = "stablecoin_flows.csv"
KEYWORDS = ["Tether Treasury", "USDT", "USDC", "Binance"]

# === Simulate Whale Transfers (for MVP) ===
def get_sample_data():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return [
        {"time": f"{today}T09:15:00Z", "amount": 1000000000, "token": "USDT", "from": "Tether Treasury", "to": "Binance"},
        {"time": f"{today}T14:00:00Z", "amount": 300000000, "token": "USDC", "from": "Circle", "to": "Unknown Wallet"},
        {"time": f"{today}T18:30:00Z", "amount": 500000000, "token": "USDT", "from": "Tether Treasury", "to": "Binance"},
        {"time": f"{today}T22:00:00Z", "amount": 250000000, "token": "USDC", "from": "Circle", "to": "Coinbase"},
    ]

def save_flows_to_csv(data):
    # Avoid duplicate rows by tracking existing timestamps
    existing = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing = {row["Timestamp"] + row["Stablecoin"] + row["Destination"] for row in reader}

    with open(OUTPUT_FILE, mode="a", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Timestamp", "Amount", "Stablecoin", "Source", "Destination"])
        if f.tell() == 0:
            writer.writeheader()

        for row in data:
            key = row["time"] + row["token"] + row["to"]
            if key not in existing:
                writer.writerow({
                    "Timestamp": row["time"],
                    "Amount": row["amount"],
                    "Stablecoin": row["token"],
                    "Source": row["from"],
                    "Destination": row["to"]
                })

# === Summarize past 24h Stablecoin Flows ===
def summarize_stablecoin_flows():
    inflow = 0
    outflow = 0
    try:
        with open(OUTPUT_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = datetime.strptime(row["Timestamp"], "%Y-%m-%dT%H:%M:%SZ")
                if ts >= datetime.utcnow() - timedelta(hours=24):
                    amount = float(row["Amount"])
                    destination = row["Destination"].lower()
                    if "binance" in destination or "coinbase" in destination:
                        inflow += amount
                    elif "unknown" in destination or "wallet" in destination:
                        continue
                    else:
                        outflow += amount
    except Exception as e:
        print("❌ Error reading stablecoin_flows.csv:", e)

    return inflow, outflow

# === Format a Human-Readable Summary ===
def format_stablecoin_summary():
    inflow, outflow = summarize_stablecoin_flows()
    lines = []
    if inflow > 0:
        lines.append(f"🟢 Inflow: ${inflow:,.0f}")
    if outflow > 0:
        lines.append(f"🔴 Outflow: ${outflow:,.0f}")
    if not lines:
        lines.append("No major stablecoin flow in past 24h.")
    return "\n".join(lines)

# === Manual Test Run ===
if __name__ == "__main__":
    print("📥 Saving sample stablecoin flow data...")
    sample_data = get_sample_data()
    save_flows_to_csv(sample_data)
    inflow, outflow = summarize_stablecoin_flows()
    print("\n✅ 24h Stablecoin Flow Summary:")
    print(format_stablecoin_summary())