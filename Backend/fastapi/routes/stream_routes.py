import logging
import math
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from Backend.helper.encrypt import decode_string

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dl/{encoded_id}/video.mkv")
@router.head("/dl/{encoded_id}/video.mkv")
async def stream_video(encoded_id: str, request: Request):
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

    # Align offset to 1MB boundary — fixes OFFSET_INVALID error
    CHUNK_SIZE = 1024 * 1024
    offset = (start // CHUNK_SIZE) * CHUNK_SIZE
    first_part_cut = start - offset
    content_length = end - start + 1

    headers = {
        "Content-Type": mime_type,
        "Content-Length": str(content_length),
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
    }

    async def file_generator():
        sent = 0
        skip_bytes = first_part_cut
        limit = math.ceil((end - offset + 1) / CHUNK_SIZE)
        async for chunk in bot.stream_media(message, offset=offset, limit=limit):
            chunk_data = bytes(chunk)
            if skip_bytes > 0:
                chunk_data = chunk_data[skip_bytes:]
                skip_bytes = 0
            if sent + len(chunk_data) > content_length:
                chunk_data = chunk_data[:content_length - sent]
            sent += len(chunk_data)
            yield chunk_data
            if sent >= content_length:
                break

    status_code = 206 if range_header else 200
    return StreamingResponse(file_generator(), status_code=status_code, headers=headers)
