from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_ID = os.getenv("CHAT_ID")
OWNER_ID = os.getenv("OWNER_ID")

print("[DEBUG] TELEGRAM_TOKEN =", TELEGRAM_TOKEN)
print("[DEBUG] OPENAI_API_KEY =", OPENAI_API_KEY)
print("[DEBUG] CHAT_ID =", CHAT_ID)
print("[DEBUG] OWNER_ID =", OWNER_ID)


