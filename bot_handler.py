# bot_handler.py

import os
import csv
import json
from datetime import datetime
from dotenv import load_dotenv

from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import ParseMode

from telegram_gating import (
    handle_register_command,
    get_subscription_status,
)

from config import TELEGRAM_BOT_TOKEN, VIP_CHAT_ID
from daily_summary import (
    load_signals_for_today,
    load_upcoming_events,
    format_summary,
)

load_dotenv()
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")

INVITE_LINK = "https://t.me/+JrB0OfuXwvs2NjQ1"
DB_FILE = "subscriber_db.csv"

# === Logging ===
def log_event(msg: str):
    os.makedirs("logs", exist_ok=True)
    with open("logs/bot_events.log", "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

# === /start ===
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_text(
        f"👋 Hello {user.first_name or 'there'}!\n\n"
        "<b>Welcome to iCryptoPulse AI</b>\n\n"
        "📢 Free-tier users get TA summaries & low-confidence alerts.\n"
        "💳 Use <b>/subscribe</b> to start a 1-month VIP trial.\n"
        "📥 After subscribing, use:\n"
        "<code>/register your_email@example.com</code>\n\n"
        "ℹ️ Use <b>/explain</b> to understand signals & confidence.\n"
        "🔎 Use <b>/about</b> to see how this bot works.\n"
        "❓ Need help? Type <b>/help</b> anytime.",
        parse_mode=ParseMode.HTML
    )
    log_event(f"User {user.id} started bot")

# === /subscribe ===
def subscribe(update: Update, context: CallbackContext):
    update.message.reply_text(
        f"🚀 Join the VIP Channel:\n{INVITE_LINK}\n\n"
        "📌 Make sure you complete your subscription payment first."
    )
    log_event(f"Sent invite link to {update.effective_user.id}")

# === /register ===
def register(update: Update, context: CallbackContext):
    try:
        args = context.args
        if len(args) != 1:
            update.message.reply_text("Usage: /register your_email@example.com")
            return

        email = args[0]
        telegram_id = update.effective_user.id

        response = handle_register_command(telegram_id, email)
        update.message.reply_text(response)

    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

# === /addvip ===
def addvip(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        update.message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        args = context.args
        if len(args) != 1:
            update.message.reply_text("Usage: /addvip <telegram_id>")
            return

        target_id = args[0]
        updated = False
        rows = []

        with open(DB_FILE, "r") as f:
            reader = csv.reader(f)
            rows = list(reader)

        for i, row in enumerate(rows):
            if i == 0:
                continue
            if row[0] == target_id:
                rows[i][3] = "1"  # is_vip
                updated = True

        if updated:
            with open(DB_FILE, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerows(rows)
            update.message.reply_text(f"✅ User {target_id} upgraded to VIP.")
        else:
            update.message.reply_text(f"❌ Could not find Telegram ID: {target_id}")

    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

# === /summary ===
def summary(update: Update, context: CallbackContext):
    telegram_id = str(update.effective_user.id)
    is_paid, is_vip, _ = get_subscription_status(telegram_id)

    if not (is_paid or is_vip):
        update.message.reply_text("🚫 VIP access only. Use /register to link your subscription.")
        return

    try:
        signals = load_signals_for_today()
        events = load_upcoming_events()
        message = format_summary(signals, events)

        update.message.reply_text(message, parse_mode="Markdown")
    except Exception as e:
        update.message.reply_text("❌ Error generating summary.")
        print("Error in /summary:", e)

# === /explain ===
def explain(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📊 *Signal & Confidence Explained:*\n\n"
        "• *Signal* — AI’s interpretation of the news for an asset:\n"
        "  - BUY = bullish\n  - SELL = bearish\n  - HOLD = no bias\n\n"
        "• *Confidence (%)* — How reliable the AI thinks the signal is.\n"
        "It considers news quality, sentiment clarity, ticker match, and contradictions.\n\n"
        "⚠️ *This is not financial advice.*",
        parse_mode="Markdown"
    )

def forcepost(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        update.message.reply_text("🚫 Only authorized admins can use /forcepost.")
        return

    args = context.args
    if len(args) < 3:
        update.message.reply_text("Usage: /forcepost <ASSET> <BUY/SELL/HOLD> <CONFIDENCE%> [Reason]")
        return

    asset = args[0].upper()
    signal = args[1].upper()
    confidence = args[2]
    reason = " ".join(args[3:]) if len(args) > 3 else "Manual test signal."

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    message = f"""🚨 *Manual Signal Override*
📊 Signal from admin for {asset}: {signal}
📈 Confidence: {confidence}%
💬 {reason}
🕒 {now}

🔎 *This is a manually posted test. Not financial advice.*
"""

    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        bot.send_message(chat_id=VIP_CHAT_ID, text=message, parse_mode=ParseMode.HTML)
        update.message.reply_text("✅ Signal sent to VIP channel.")
    except Exception as e:
        update.message.reply_text(f"❌ Failed to post signal: {e}")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "<b>🆘 iCryptoPulse AI — Help</b>\n\n"
        "<b>Available Commands:</b>\n"
        "• /start — Start the bot\n"
        "• /about — How iCryptoPulse works\n"
        "• /explain — Signal & confidence explanation\n"
        "• /subscribe — Start VIP trial\n"
        "• /register your_email@example.com — Link subscription\n"
        "• /summary — Daily VIP summary\n"
        "• /status — System status (VIP/Admin)\n\n"
        "<b>Signal Types:</b>\n"
        "• 🟢 BUY / 🔴 SELL — High-confidence signals\n"
        "• ⚠️ Low-Confidence — Awareness only\n"
        "• TA-only updates when news is quiet\n\n"
        "⚠️ <i>Not financial advice. Educational use only.</i>",
        parse_mode=ParseMode.HTML
    )

def about(update: Update, context: CallbackContext):
    update.message.reply_text(
        "<b>ℹ️ About iCryptoPulse AI</b>\n\n"
        "iCryptoPulse AI delivers <b>news-driven crypto signals</b> "
        "combined with <b>real-time technical indicators</b>.\n\n"
        "<b>How it works:</b>\n"
        "1️⃣ Scan trusted crypto news\n"
        "2️⃣ AI filters noise & low-quality content\n"
        "3️⃣ Signals validated with RSI, MA & volume\n"
        "4️⃣ Only liquid, high-volume Binance futures used\n\n"
        "<b>User Tiers:</b>\n"
        "• 🆓 Free — TA summaries & low-confidence alerts\n"
        "• ⭐ VIP — High-confidence signals & summaries\n"
        "• 🛡 VVIP — Permanent VIP (invite-only)\n\n"
        "💳 New users get <b>1 month VIP free</b>.\n\n"
        "⚠️ <i>This bot does NOT provide financial advice.</i>\n"
        "AI-generated insights for learning & research.",
        parse_mode=ParseMode.HTML
    )

# === Boot the Bot ===
def main():
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("subscribe", subscribe))
    dp.add_handler(CommandHandler("register", register))
    dp.add_handler(CommandHandler("addvip", addvip))
    dp.add_handler(CommandHandler("summary", summary))
    dp.add_handler(CommandHandler("explain", explain))
    dp.add_handler(CommandHandler("forcepost", forcepost))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("about", about))

    print("🤖 Bot is running. Press Ctrl+C to stop.")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()