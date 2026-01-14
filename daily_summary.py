# daily_summary.py

import os
import csv
import json
from datetime import datetime
from telegram import Bot
from dotenv import load_dotenv

# === LOAD CONFIG ===
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY", "")
VIP_CHAT_ID = os.getenv("VIP_CHAT_ID")
ADMIN_IDS = os.getenv("ADMIN_IDS", "")

SIGNAL_LOG = "signals_log.csv"
EVENTS_FILE = "weekly_events.json"


def load_signals_for_today():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    signals = []

    try:
        with open(SIGNAL_LOG, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Timestamp"].startswith(today) and row["Confidence"]:
                    try:
                        conf = int(float(row["Confidence"]))
                        if conf >= 70:
                            signals.append({
                                "asset": row.get("Asset", "UNKNOWN"),
                                "signal": row.get("Signal", ""),
                                "confidence": conf,
                                "title": row.get("Title", "")[:100],
                                "rsi": row.get("RSI", ""),
                                "volume": row.get("Volume", "")
                            })
                    except:
                        continue
    except:
        return []

    return sorted(signals, key=lambda x: x["confidence"], reverse=True)

def load_upcoming_events():
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            events = json.load(f)
            return events
    except:
        return []

def load_recent_skip_summary(limit=1):
    try:
        with open("skipped_signals_log.csv", newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
            today = datetime.utcnow().strftime("%Y-%m-%d")
            skips = [r for r in rows if r["Timestamp"].startswith(today)]
            return skips[-limit:] if skips else []
    except:
        return []

def format_summary(signals, events):
    lines = []

    today = datetime.utcnow().strftime("%A, %b %d")
    lines.append(f"📊 *iCryptoPulse Daily Recap — {today}*\n")

    # === Optional: Show last skipped article
    skipped = load_recent_skip_summary()
    if skipped:
        s = skipped[0]
        lines.append("\n🛑 *Most Recent Skipped News:*")
        lines.append(f"- {s['Title']} ({s['Source']}, Score: {s['Score']}) — {s['Reason']}")

    # === Top Signals
    if signals:
        lines.append("🧠 *Top Signals:*")
        for s in signals[:3]:
            lines.append(f"- {s['asset']}: {s['signal']} ({s['confidence']}%) — {s['title']}")
    else:
        lines.append("🧠 *Top Signals:* No strong signals today.")

    # === Technical Tags Summary
    high_rsi = [s["asset"] for s in signals if s.get("rsi") and float(s["rsi"]) > 70]
    spike_vol = [s["asset"] for s in signals if s.get("volume") and "High" in s["volume"]]

    if high_rsi or spike_vol:
        lines.append("\n🔍 *Technical Highlights:*")
        if high_rsi:
            lines.append(f"- RSI Overbought: {', '.join(high_rsi)}")
        if spike_vol:
            lines.append(f"- Volume Spikes: {', '.join(spike_vol)}")

    # === Event Outlook
    if events:
        lines.append("\n🗓️ *This Week's Catalysts:*")
        for e in events:
            lines.append(f"- {e['day']}: {e['event']}")
    else:
        lines.append("\n🗓️ No event data available.")

    lines.append("\n📌 All signals are AI-generated. Not financial advice.")
    return "\n".join(lines)

def send_to_telegram(message):
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        bot.send_message(chat_id=VIP_CHAT_ID, text=message, parse_mode="Markdown")
        print("✅ Daily summary sent to Telegram.")
    except Exception as e:
        print(f"❌ Failed to send daily summary: {e}")

def main():
    signals = load_signals_for_today()
    events = load_upcoming_events()
    summary = format_summary(signals, events)
    print(summary)
    send_to_telegram(summary)

if __name__ == "__main__":
    main()