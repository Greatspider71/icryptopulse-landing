# usdt_printer.py
# Track USDT flows from Tether Treasury on Ethereum (V2) and Tron

import requests
import csv
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
# Default URL, though we redefine it inside the function to be safe with the .org fix
TRON_API_URL = "https://apilist.tronscan.org/api/token_trc20/transfers"

# Addresses
ETH_TREASURY = "0x5754284f345afc66a98fbb0a0a7eaef6a5be05da"
TRON_TREASURY = "TBP6Xx4sqz9ABCP1pW9HK8aM28P4Ljsa75"
TRON_USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

OUTPUT_FILE = "stablecoin_flows.csv"


def fetch_eth_usdt_mints():
    """Fetches USDT outflows (injections) from Ethereum Treasury using Etherscan V2."""

    # --- V2 UPDATE: New URL + chainid=1 ---
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": "1",  # Required for V2 (1 = Ethereum Mainnet)
        "module": "account",
        "action": "tokentx",
        "address": ETH_TREASURY,
        "contractaddress": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10).json()

        # Check for valid response
        if response.get("status") != "1" or not isinstance(response.get("result"), list):
            if response.get("message") == "No transactions found":
                return []

            print("⚠️ Etherscan V2 Error:")
            print(json.dumps(response, indent=2))
            return []

        data = response["result"]
        parsed = []

        for tx in data:
            # Filter: Money LEAVING the Treasury = Injection (Mint)
            if tx["to"].lower() == ETH_TREASURY.lower():
                continue

            amount = int(tx["value"]) / 10 ** 6
            timestamp = datetime.fromtimestamp(int(tx["timeStamp"]))

            if amount < 10_000_000:  # Only alert if > $10 Million
                continue

            parsed.append({
                "Timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Amount": amount,
                "Stablecoin": "USDT",
                "Chain": "Ethereum",
                "Source": "Tether Treasury",
                "Destination": tx["to"]
            })

        return parsed

    except Exception as e:
        print("❌ Error fetching Ethereum USDT mints:", e)
        return []


def fetch_tron_usdt_mints():
    """Fetches USDT outflows (injections) from Tron Treasury."""

    # Get Key from .env
    tron_key = os.getenv("TRONSCAN_API_KEY")

    headers = {
        "TRON-PRO-API-KEY": tron_key
    }

    # Use the .org domain and 'address' parameter
    TRON_API_URL = "https://apilist.tronscan.org/api/token_trc20/transfers"
    params = {
        "limit": 50,
        "start": 0,
        "contract_address": TRON_USDT_CONTRACT,
        "address": TRON_TREASURY,
    }

    try:
        response_json = requests.get(TRON_API_URL, params=params, headers=headers, timeout=10).json()

        data = response_json.get("token_transfers", [])
        parsed = []

        for tx in data:
            if tx["to_address"] == TRON_TREASURY:
                continue

            amount = float(tx["quant"]) / 10 ** 6
            timestamp = datetime.fromtimestamp(int(tx["block_ts"]) / 1000)

            if amount < 10_000_000:  # Only alert if > $10 Million
                continue

            parsed.append({
                "Timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Amount": amount,
                "Stablecoin": "USDT",
                "Chain": "Tron",
                "Source": "Tether Treasury",
                "Destination": tx["to_address"]
            })

        if not parsed and len(data) == 0:
            print(f"ℹ️ Tron returned 0 transactions. (Check your API Key)")

        return parsed

    except Exception as e:
        print("❌ Error fetching Tron USDT mints:", e)
        return []


def save_to_csv(data):
    file_exists = os.path.isfile(OUTPUT_FILE)
    if not data:
        return

    with open(OUTPUT_FILE, mode="a", newline="", encoding="utf-8") as f:
        fieldnames = ["Timestamp", "Amount", "Stablecoin", "Chain", "Source", "Destination", "FlowType"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for row in data:
            # Classify the flow
            to_addr = row["Destination"].lower()
            if "binance" in to_addr:
                row["FlowType"] = "Exchange Inflow"
            elif "kucoin" in to_addr:
                row["FlowType"] = "Exchange Inflow"
            elif "huobi" in to_addr or "htx" in to_addr:
                row["FlowType"] = "Exchange Inflow"
            elif "wallet" in to_addr or to_addr.startswith("0x"):
                row["FlowType"] = "Unknown"
            else:
                row["FlowType"] = "Other"
            writer.writerow(row)


def main():
    key = os.getenv("TRONSCAN_API_KEY")
    if key:
        print(f"🔑 TRON Key Found: {key[:4]}...{key[-4:]}")
    else:
        print("❌ NO TRON KEY FOUND. Check your .env file naming!")

    print("📡 Fetching USDT flows from Tether Treasury (Etherscan V2 + Tron)...")

    eth_data = fetch_eth_usdt_mints()
    tron_data = fetch_tron_usdt_mints()

    all_data = eth_data + tron_data
    total_new = len(all_data)

    if total_new > 0:
        save_to_csv(all_data)
        print(f"✅ Saved {total_new} transactions to {OUTPUT_FILE}")
        print(f"   Latest: {all_data[0]['Amount']:,.0f} USDT on {all_data[0]['Chain']}")
    else:
        print("⚠️ No new INJECTIONS found (> $10M) today.")


if __name__ == "__main__":
    main()