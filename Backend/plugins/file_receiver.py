"""
file_receiver.py — Telegram bot plugin for receiving uploaded videos.

REUSED from original:
  - PyroFork message handler pattern
  - File size formatting
  - encode_string for Telegram file ID
  - AUTH_CHANNEL check

REPLACED:
  - Caption parsing (title/year/quality extraction) → removed entirely
  - TMDB metadata fetch → removed entirely
  - MovieSchema/TVShowSchema creation → VideoSchema creation
  - Quality replacement logic → not needed (each upload is a new video)

New behaviour:
  When you upload a video to your channel, the bot saves it with the
  original filename as the title. You can rename it later in the admin panel.
"""

import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from Backend.config import Telegram
from Backend.helper.encrypt import encode_string

logger = logging.getLogger(__name__)


def get_readable_file_size(size_in_bytes: int) -> str:
    """REUSED from original project."""
    if size_in_bytes is None:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} PB"


async def handle_video(client: Client, message: Message):
    """
    Handles incoming video/document messages in AUTH_CHANNEL.
    Saves them to MongoDB with original filename as title.
    No TMDB, no caption parsing — just store and let user rename later.
    """
    from Backend import db

    # Only process files from our auth channel
    if message.chat.id != Telegram.AUTH_CHANNEL:
        return

    # Get file info
    media = message.video or message.document
    if not media:
        return

    original_filename = getattr(media, "file_name", None) or f"video_{message.id}.mp4"
    file_size = get_readable_file_size(getattr(media, "file_size", 0))

    # Encode Telegram reference — same as original project
    encoded_id = encode_string(message.chat.id, message.id)

    # Use filename (without extension) as default title
    title = original_filename.rsplit(".", 1)[0] if "." in original_filename else original_filename

    try:
        video_id = await db.add_video(
            title=title,
            original_filename=original_filename,
            encoded_id=encoded_id,
            file_size=file_size,
            folder_id="root"
        )
        logger.info(f"New video saved: '{title}' | ID: {video_id}")
    except Exception as e:
        logger.error(f"Failed to save video: {e}")


def register(app: Client):
    """Register the file receiver handler with the Pyrogram client."""

    @app.on_message(
        filters.chat(Telegram.AUTH_CHANNEL) &
        (filters.video | filters.document)
    )
    async def _handler(client: Client, message: Message):
        await handle_video(client, message)

    logger.info("File receiver plugin loaded.")
    print("DEBUG: file_receiver.py PLUGIN LOADED SUCCESSFULLY!")
