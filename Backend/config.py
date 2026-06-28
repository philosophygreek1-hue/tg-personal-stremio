import os
from dotenv import load_dotenv

load_dotenv("config.env")

class Config:
    # Telegram
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    OWNER_ID = int(os.environ.get("OWNER_ID", 0))
    AUTH_CHANNEL = int(os.environ.get("AUTH_CHANNEL", 0))

    # Database — single URI for personal use
    DATABASE = os.environ.get("DATABASE", "")

    # Server
    BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
    PORT = int(os.environ.get("PORT", 8000))

    # Admin
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")

    # Update
    UPSTREAM_REPO = os.environ.get("UPSTREAM_REPO", "")
    UPSTREAM_BRANCH = os.environ.get("UPSTREAM_BRANCH", "master")

Telegram = Config()
