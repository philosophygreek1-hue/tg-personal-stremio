"""
stream_routes.py — Telegram file streaming endpoint.

REUSED from original project almost entirely.
The /dl/{encoded_id}/video.mkv endpoint decodes the Telegram
chat_id + message_id and streams the file via PyroFork.

Only change: simplified imports (no multi-token load balancer needed).
"""

import logging
import math
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from Backend.helper.encrypt import decode_string
from Backend.config import Telegram

logger = logging.getLogger(__name__)
router = APIRouter()

CHUNK_SIZE = 1024 * 1024  # 1MB chunks


@router.get("/dl/{encoded_id}/video.mkv")
@router.head("/dl/{encoded_id}/video.mkv")
async def stream_video(encoded_id: str, request: Request):
    """
    Stream a Telegram file by its encoded ID.
    REUSED from original project — decodes chat_id + message_id,
    uses PyroFork to stream chunks directly to the client.
    """
    from Backend import bot

    try:
        chat_id, message_id = decode_string(encoded_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid stream ID")

    try:
        message = await bot.get_messages(chat_id, message_id)
    except Exception as e:
        logger.error(f"Could not fetch Telegram message: {e}")
        raise HTTPException(status_code=404, detail="File not found")

    media = message.video or message.document
    if not media:
        raise HTTPException(status_code=404, detail="No media in message")

    file_size = media.file_size
    mime_type = getattr(media, "mime_type", "video/mp4")

    # Range request handling — same as original
    range_header = request.headers.get("Range")
    start = 0
    end = file_size - 1

    if range_header:
        try:
            range_val = range_header.replace("bytes=", "")
            parts = range_val.split("-")
            start = int(parts[0])
            end = int(parts[1]) if parts[1] else file_size - 1
        except Exception:
            pass

    content_length = end - start + 1
    headers = {
        "Content-Type": mime_type,
        "Content-Length": str(content_length),
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
    }

    async def file_generator():
        offset = start
        remaining = content_length
        async for chunk in bot.stream_media(message, offset=offset, limit=math.ceil(remaining / CHUNK_SIZE)):
            chunk_data = bytes(chunk)
            if remaining <= 0:
                break
            if len(chunk_data) > remaining:
                chunk_data = chunk_data[:remaining]
            remaining -= len(chunk_data)
            yield chunk_data

    status_code = 206 if range_header else 200
    return StreamingResponse(file_generator(), status_code=status_code, headers=headers)
