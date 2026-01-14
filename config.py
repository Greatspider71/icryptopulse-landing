import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
VIP_CHAT_ID = os.getenv("VIP_CHAT_ID")
ADMIN_IDS = os.getenv("ADMIN_IDS")
CRYPTOPANIC_API_KEY =os.getenv("CRYPTOPANIC_API_KEY")
