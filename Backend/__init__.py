"""
Backend/__init__.py — Application entry point.

REUSED from original:
  - Pyrogram client initialization
  - Database initialization
  - Plugin loading pattern
  - Uvicorn startup

REMOVED:
  - TMDB client initialization
  - Helper bot (not needed for personal use)
  - Multi-token system
"""

import asyncio
import importlib
import logging
import uvicorn
from pyrogram import Client
from Backend.config import Telegram
from Backend.helper.database import Database

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%d-%b-%y %I:%M:%S %p"
)
logger = logging.getLogger(__name__)

# Global instances — same pattern as original
bot: Client = None
db: Database = None


async def start():
    global bot, db

    logger.info("Initializing Personal Video Stremio Server...")

    # Database
    db = Database()

    # Telegram bot — same PyroFork client setup as original
    bot = Client(
        name="PersonalVideoBot",
        api_id=Telegram.API_ID,
        api_hash=Telegram.API_HASH,
        bot_token=Telegram.BOT_TOKEN,
        in_memory=True,
    )

    # Load plugins — same pattern as original
    plugins = ["Backend.plugins.file_receiver"]
    for plugin in plugins:
        try:
            module = importlib.import_module(plugin)
            module.register(bot)
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin}: {e}")

    await bot.start()
    me = await bot.get_me()
    logger.info(f"Bot started: @{me.username}")

    logger.info("Starting web server...")
    from Backend.fastapi.app import app
    config = uvicorn.Config(app, host="0.0.0.0", port=Telegram.PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def main():
    asyncio.run(start())


if __name__ == "__main__":
    main()
