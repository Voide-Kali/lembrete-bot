"""Exemplo de configuração do bot de lembretes."""

import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = (
    os.environ.get("LEMBRETE_TELEGRAM_TOKEN")
    or os.environ.get("TELEGRAM_TOKEN")
    or os.environ.get("TELEGRAM_BOT_TOKEN")
    or ""
)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile")
TIMEZONE = os.environ.get("TIMEZONE", "America/Campo_Grande")
ALLOWED_CHAT_ID = int(os.environ.get("ALLOWED_CHAT_ID", "0"))
