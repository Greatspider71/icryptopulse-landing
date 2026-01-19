import re
import sys
import os
from dotenv import load_dotenv

# === Setup ===
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
from telegram import Bot
from openai import OpenAI
import csv
from contradiction_filter import has_contradiction
import feedparser
from symbol_map import symbol_map
# Reverse mapping: ticker -> base token (e.g. XRPUSDT -> XRP)
symbol_to_token = {v: k for k, v in symbol_map.items()}

from gpt_cache import get_cached_result, save_cached_result
from confidence import calibrate_confidence
from hashlib import md5
from datetime import datetime, timedelta
from technical_indicators import get_technical_indicators, get_market_change_summary
import subprocess
from symbol_map import symbol_map

# === LOAD CONFIG ===
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "")

client = OpenAI(api_key=OPENAI_API_KEY)

POSTED_IDS_FILE = "posted_ids.txt"
CSV_FILE = "signals_log.csv"
PENDING_PRICES_FILE = "pending_prices.csv"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/ticker/price"


# Update symbol_map daily
subprocess.run(["python3", "symbol_map_updater.py"])

# === CONFIG ===
from config import OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# Reverse mapping: symbol (e.g. BTCUSDT) → token (e.g. BTC)
symbol_to_token = {v: k for k, v in symbol_map.items()}

# Load top 50 volume tickers (from latest Binance 24h data)
with open("top_volume_tickers.txt") as f:
    TOP_VOLUME_TICKERS = set(line.strip() for line in f if line.strip())

# === Dynamic major asset detection (first 30 tokens by name length or popularity) ===
# You can customize which symbols are always respected as 'major'

MAJOR_ASSETS = set()

# Add all base symbols (keys) from the symbol map that are 3–6 characters (common for major coins)
for token in symbol_map:
    if 3 <= len(token) <= 6:
        MAJOR_ASSETS.add(token.upper())

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://www.theblock.co/rss",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://www.dlnews.com/rss/",
    "https://cryptoslate.com/feed/",
    "https://dailyhodl.com/feed/",
    "https://beincrypto.com/feed/",
    "https://u.today/rss"
]

# === UTILS ===
def get_symbol_for_title(title):
    title_upper = title.upper()
    title_words = set(re.findall(r'\b[A-Z0-9]{2,12}\b', title_upper))  # e.g. BTC, DOGE, SHIB, XRP

    for token, symbol in symbol_map.items():
        if token.upper() in title_words:
            return symbol
    return None

def load_posted_ids():
    if not os.path.exists(POSTED_IDS_FILE):
        return set()
    with open(POSTED_IDS_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_posted_id(news_id):
    with open(POSTED_IDS_FILE, "a") as f:
        f.write(f"{news_id}\n")

def log_skipped_news(title, summary, source, reason, score, category):
    filename = "skipped_signals_log.csv"
    fieldnames = ["Timestamp", "Title", "Source", "Score", "Category", "Reason", "Summary"]
    row = {
        "Timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "Title": title,
        "Source": source,
        "Score": score,
        "Category": category,
        "Reason": reason,
        "Summary": summary
    }
    file_exists = os.path.isfile(filename)
    with open(filename, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def log_to_csv(signal, label, confidence, title, reason, url, chart_link, ticker, price_at_signal, technicals):
    row = {
        "Timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "Signal": signal,
        "Label": label,
        "Confidence": confidence,
        "Title": title,
        "Reason": reason,
        "Asset": ticker,
        "Price_at_Signal": price_at_signal,
        "Price_after_3h": "",
        "Price_Change_%": "",
        "URL": url,
        "ChartLink": chart_link or "",
        "RSI": technicals.get("rsi", ""),
        "Volume": technicals.get("volume_spike", "")
    }
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    # Also add to pending_prices.csv
    with open(PENDING_PRICES_FILE, mode='a', newline='', encoding='utf-8') as f:
        pending_writer = csv.DictWriter(f, fieldnames=["Timestamp", "Asset", "Price_at_Signal", "Check_After"])
        if not os.path.exists(PENDING_PRICES_FILE) or os.path.getsize(PENDING_PRICES_FILE) == 0:
            pending_writer.writeheader()
        check_after = (datetime.utcnow() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")
        pending_writer.writerow({
            "Timestamp": row["Timestamp"],
            "Asset": ticker,
            "Price_at_Signal": price_at_signal,
            "Check_After": check_after
        })

def send_telegram_message(text):
    try:
        with open("authorized_channels.txt", "r") as f:
            chat_ids = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print("⚠️ No authorized_channels.txt file found. No messages will be sent.")
        return
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    for chat_id in chat_ids:
        try:
            bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        except Exception as e:
            print(f"❌ Failed to send message to {chat_id}: {e}")

def generate_news_id(entry):
    raw_id = (entry.link + entry.get("published", "")).encode("utf-8")
    return md5(raw_id).hexdigest()

def get_rss_news():
    all_entries = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            all_entries.append({
                "id": generate_news_id(entry),
                "title": entry.title,
                "summary": entry.get("summary", ""),
                "url": entry.link,
                "published": entry.get("published", ""),
                "source": feed.feed.get("title", "Unknown")
            })
    return all_entries

def evaluate_news_quality_with_gpt(title, summary, source=None):
    prompt = f"""
You are an AI signal filter. Evaluate the following crypto news:
Include: TRUE or FALSE
Score: <0-100>
Type: <Listing, Regulation, Hack, Upgrade, Macro, Whale, etc>
Reason: <Brief explanation in your own words>

📄 Source: {source or "Unknown"}
Title: {title}
Summary: {summary}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        lines = response.choices[0].message.content.strip().splitlines()
        result = {"include": False, "score": 0, "type": "Unknown", "reason": "Not parsed"}
        for line in lines:
            if line.startswith("Include:"):
                result["include"] = "TRUE" in line.upper()
            elif line.startswith("Score:"):
                result["score"] = int("".join(filter(str.isdigit, line)))
            elif line.startswith("Type:"):
                result["type"] = line.split(":", 1)[1].strip()
            elif line.startswith("Reason:"):
                result["reason"] = line.split(":", 1)[1].strip()
        return result
    except Exception as e:
        print("❌ GPT filter error:", e)
        return {"include": False, "score": 0, "type": "Error", "reason": "GPT call failed"}

def classify_news_with_gpt(title, content, asset, timestamp, source, market_change, has_conflict, technicals):
    context = f"""
News Title: {title}
Summary: {content}
Asset: {asset}
Time: {timestamp}
Source: {source}
Market Change: {market_change}
Contradiction Flag: {has_conflict}
Technical Indicators:
- RSI: {technicals['rsi']} ({technicals['rsi_label']})
- MA Crossover: {technicals['ma_crossover']}
- Volume Spike: {technicals['volume_spike']}
"""
    prompt = f"""
You are an AI signal analyst. Interpret the news + technical indicators.
Return this format:
Signal: BUY/SELL/HOLD
Label: 🟢/🔴/⚪️
Confidence: <0-100>%
Reason: <In your own words, no quotes>

{context}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        lines = response.choices[0].message.content.strip().splitlines()
        return (
            lines[0].split(":", 1)[1].strip().upper(),
            lines[1].split(":", 1)[1].strip(),
            lines[2].split(":", 1)[1].replace("%", "").strip(),
            lines[3].split(":", 1)[1].strip()
        )
    except Exception as e:
        print("❌ GPT classification error:", e)
        return "HOLD", "⚪️ Neutral", "50", "No reason (GPT error)"

def guess_ticker_from_gpt(title, summary):
    prompt = f"""
You are a crypto analyst.
Based on the news below, guess ONE most relevant Binance USDT perpetual futures symbol
(e.g. BTCUSDT, ETHUSDT, XRPUSDT).

Rules:
- Only return ONE symbol
- Must end with USDT
- If unsure, return NONE

Title: {title}
Summary: {summary}
"""

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        guess = res.choices[0].message.content.strip().upper()

        # === HARD GUARDS ===
        if guess == "NONE":
            return None

        # must end with USDT
        if not guess.endswith("USDT"):
            return None

        # must exist in Binance symbol map
        # ✅ Validate GPT guess
        if guess not in symbol_map.values():
            print(f"⚠️ GPT guessed invalid ticker: {guess}")
            return None

        if guess not in TOP_VOLUME_TICKERS:
            print(f"⚠️ GPT guessed low-volume ticker (filtered): {guess}")
            return None

        return guess

    except Exception as e:
        print("❌ GPT ticker guess error:", e)
        return None

def get_futures_price(symbol):
    try:
        r = requests.get(BINANCE_FUTURES_URL, params={"symbol": symbol})
        return float(r.json()["price"])
    except:
        return None

def is_ticker_consistent_with_context(ticker, title, summary):
    """
    Ensure the selected ticker is explicitly referenced in the news title or summary.
    This prevents false matches like ACTUSDT from 'CLARITY ACT'.
    """
    base_token = symbol_to_token.get(ticker)
    if not base_token:
        return False

    content = f"{title} {summary}".upper()

    # Direct token match
    if base_token in content:
        return True

    # Alias-based matching (expand as needed)
    token_aliases = {
        "BTC": ["BITCOIN"],
        "ETH": ["ETHEREUM"],
        "XRP": ["RIPPLE"],
        "DOGE": ["DOGECOIN"],
        "SHIB": ["SHIBA", "SHIBA INU"],
        "PEPE": ["PEPECOIN"],
        "ADA": ["CARDANO"],
        "SOL": ["SOLANA"],
        "BNB": ["BINANCE COIN", "BSC"],
        "DOT": ["POLKADOT"],
        "LTC": ["LITECOIN"],
        "AVAX": ["AVALANCHE"],
        "MATIC": ["POLYGON"],
    }

    for alias in token_aliases.get(base_token, []):
        if alias in content:
            return True

    return False

# === MAIN ===
def main():
    news = get_rss_news()
    print(f"Fetched {len(news)} items.")
    posted_ids = load_posted_ids()

    for item in news:
        news_id = item["id"]
        if news_id in posted_ids:
            continue

        title = item["title"]
        url = item["url"]
        summary = item["summary"]
        source = item["source"]

        cached = get_cached_result(news_id)
        if cached:
            if not cached.get("is_hard_news") or cached.get("confidence", 0) < 60:
                continue

            ticker = cached.get("ticker")
            if not ticker:
                continue

            price_at_signal = get_futures_price(ticker)
            if price_at_signal is None:
                continue

            technicals = get_technical_indicators(ticker)
            if not technicals:
                continue

            signal = cached["signal"]
            label = cached["label"]
            confidence = cached["confidence"]
            reason = cached["reason"]
            chart_link = f"https://www.tradingview.com/symbols/{ticker}/"

            contradiction_warning = ""
            if has_contradiction(ticker, signal):
                contradiction_warning = f"⚠️ *INDECISION*: Conflicting signals recently detected for *{ticker}*\n\n"

            message = f"""{contradiction_warning}📊 Signal from news for {ticker}: {signal}
{label} {title}
📈 Signal Strength Confidence: {confidence}%
🔁 RSI: {technicals['rsi']} ({technicals['rsi_label']}, {technicals['rsi_trend']})
📊 MA: {technicals['ma_crossover']}
🔊 Volume: {technicals['volume_spike']}
💬 GPT: {reason}

⚠️ This is AI-generated market insight. Not financial advice.
🔗 {url}"""

            if chart_link:
                message += f"\n📊 [View Chart]({chart_link})"

            send_telegram_message(message)
            save_posted_id(news_id)
            log_to_csv(signal, label, confidence, title, reason, url, chart_link, ticker, price_at_signal, technicals)
            continue

        # ========== Uncached ==========
        filter_result = evaluate_news_quality_with_gpt(title, summary, source)
        score = filter_result["score"]

        if not filter_result["include"] or score < 60:
            print(f"🗞️ Skipped: {title} — Score {score} ({filter_result['reason']})")
            log_skipped_news(
                title=title,
                summary=summary,
                source=source,
                reason=filter_result["reason"],
                score=score,
                category=filter_result["type"]
            )
            save_cached_result(news_id, {"is_hard_news": False})
            continue

        ticker = get_symbol_for_title(title) or guess_ticker_from_gpt(title, summary)
        if not ticker or ticker == "USDT":
            continue

        # 🚨 FINAL CONTEXT VALIDATION (title + summary vs ticker)
        if not is_ticker_consistent_with_context(ticker, title, summary):
            print(
                f"❌ BLOCKED: Ticker {ticker} not consistent with news context | "
                f"Title: {title}"
            )
            continue

        price_at_signal = get_futures_price(ticker)
        if price_at_signal is None:
            continue

        # === GPT CLASSIFICATION ===
        technicals = get_technical_indicators(ticker)
        if not technicals:
            print(f"⚠️ Skipping signal due to missing TA data for: {ticker}")
            continue

        market_change = get_market_change_summary()
        has_conflict = has_contradiction(ticker, "UNKNOWN")

        signal, label, confidence, reason = classify_news_with_gpt(
            title, summary, ticker, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), source, market_change, has_conflict, technicals
        )

        # === Signal Confidence Tier Flag ===
        low_confidence = 60 <= int(confidence) < 70
        confidence_banner = ""
        if low_confidence:
            confidence_banner = "⚠️ *Low‑Confidence Signal — For awareness only*\n\n"

        confidence = calibrate_confidence(
            raw_confidence=int(confidence),
            ticker_source="symbol_map",
            source_count=1,
            historical_price_change=None
        )

        contradiction_warning = ""
        if has_contradiction(ticker, signal):
            contradiction_warning = f"⚠️ *INDECISION*: Conflicting signals recently detected for *{ticker}*\n\n"

        save_cached_result(news_id, {
            "is_hard_news": True,
            "signal": signal,
            "label": label,
            "confidence": int(confidence),
            "reason": reason,
            "ticker": ticker,
            "ticker_source": "symbol_map"
        })

        chart_link = f"https://www.tradingview.com/symbols/{ticker}/"

        message = f"""{confidence_banner}{contradiction_warning}📊 Signal from news for {ticker}: {signal}
{label} {title}

📈 Confidence: **{confidence}%**
🔁 RSI: {technicals['rsi']} ({technicals['rsi_label']}, {technicals['rsi_trend']})
📊 MA: {technicals['ma_crossover']}
🔊 Volume: {technicals['volume_spike']}

💬 GPT: {reason}

🔎 Futures‑based indicators (5m OHLCV) · AI‑generated insight for learning · Not financial advice 
🔗 {url}
"""
        if chart_link:
            message += f"\n📊 [View Chart]({chart_link})"

        print("Sending:", message)
        send_telegram_message(message)
        save_posted_id(news_id)
        log_to_csv(signal, label, confidence, title, reason, url, chart_link, ticker, price_at_signal, technicals)

if __name__ == "__main__":
    main()
