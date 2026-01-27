# daily_summary.py

import os
import csv
import json
from datetime import datetime
from usdt_printer import summarize_usdt_flows
from liquidation_map import load_liquidation_summary
from narrative_heatmap import analyze_sector_narratives
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

# === Load Liquidation Heatmap ===
def load_liquidation_summary():
    try:
        with open("liquidation_summary.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "No liquidation data available."


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
                                "volume": row.get("Volume", ""),
                            })
                    except:
                        continue
    except:
        return []

    return sorted(signals, key=lambda x: x["confidence"], reverse=True)

def load_upcoming_events():
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
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


def generate_actionable_takeaway(signals, inflow, outflow, liquidation_text, narrative_text):
    """
    Synthesizes a plain-English strategy summary from current data.
    """
    if signals:
        main_asset = signals[0].get("asset", "")
        conf = signals[0].get("confidence", "")
        direction = signals[0].get("signal", "")
        return f"📌 <b>Strategy Insight:</b>\nMarket confidence leans <b>{direction.lower()}</b> on {main_asset} ({conf}%). Watch for confirmation or contradiction in the next 24h."

    # Interpret stablecoin inflow/outflow
    if inflow > outflow and inflow > 500_000_000:
        money_flow = "Whales are sending stablecoins into exchanges — potential accumulation or pre-breakout."
    elif outflow > inflow:
        money_flow = "Net outflow of stablecoins suggests risk-off behavior — watch for dips."
    else:
        money_flow = "Stablecoin flows neutral — market may remain in chop."

    # Look for key liquidation zone
    heat_lines = liquidation_text.splitlines() if liquidation_text else []
    hotspot = next((line for line in heat_lines if "████" in line or "███" in line), None)
    if hotspot:
        liq_note = f"🔥 Liquidation cluster spotted at {hotspot.split(':')[0].strip()}. Price may get magnetized there."
    else:
        liq_note = "No strong liquidation magnet detected."

    # Sector interest
    narrative_lines = narrative_text.splitlines() if narrative_text else []
    if any("🥇" in line for line in narrative_lines):
        top_sector = next(line for line in narrative_lines if "🥇" in line).split("—")[0].replace("🥇", "").strip()
        sector_note = f"Sector momentum led by <b>{top_sector}</b> plays. Rotate if breakout confirmed."
    else:
        sector_note = "No sector showing strong narrative flow yet."

    # Final summary sentence
    return (
        f"📌 <b>Strategy Insight:</b>\n"
        f"{money_flow} {liq_note} {sector_note}"
    )

def format_summary(signals, events):
    today_str = datetime.utcnow().strftime("%b %d, %Y")

    lines = [f"📊 <b>iCryptoPulse Daily Summary</b> — {today_str}\n"]

    if not signals:
        lines.append("🧠 <b>No high-confidence signals today.</b>\n")
    else:
        lines.append("🧠 <b>Top Signals:</b>")
        for s in signals[:5]:
            asset = s.get("asset", "N/A")
            signal = s.get("signal", "N/A")
            confidence = s.get("confidence", "N/A")
            title = s.get("title", "")
            lines.append(f"• <b>{asset}</b> — {signal} ({confidence}%)\n  {title}")
        lines.append("")

    # Add Stablecoin Flow Summary
    inflow, outflow = summarize_usdt_flows()
    lines.append("📥 <b>Stablecoin Flow (24h)</b>:")
    lines.append(f"🟢 Inflow: <b>${inflow:,.0f}</b>")
    lines.append(f"🔴 Outflow: <b>${outflow:,.0f}</b>\n")

    # Add Liquidation Heatmap
    heatmap = load_liquidation_summary()
    if heatmap:
        lines.append("🔥 <b>Liquidation Zones (Last 1h):</b>")
        lines.append(heatmap + "\n")

    # Add Narrative Heatmap
    narrative = analyze_sector_narratives()
    if narrative:
        lines.append("✨ <b>Narrative Heatmap (Sector Momentum)</b>:")
        lines.append(narrative + "\n")

    # Add Upcoming Events
    if events:
        lines.append("🗓️ <b>Upcoming Events:</b>")
        for e in events[:3]:
            title = e.get("title", "Unknown event")
            date = e.get("date", "")
            event_type = e.get("type", "")
            lines.append(f"• {title} ({date}) {event_type}")
    else:
        lines.append("🗓️ No event data available.")

    # === Actionable Takeaway
    takeaway = generate_actionable_takeaway(signals, inflow, outflow, heatmap, narrative)
    lines.append(takeaway)

    lines.append("\n📌 <i>All signals are AI-generated. Not financial advice.</i>")
    return "\n".join(lines)


def send_to_telegram(message):
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        bot.send_message(chat_id=VIP_CHAT_ID, text=message, parse_mode="HTML")
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