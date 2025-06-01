import os
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_ID = int(os.getenv("CHAT_ID"))
OWNER_ID = int(os.getenv("OWNER_ID"))

