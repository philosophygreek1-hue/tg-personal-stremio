import logging
import math
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from Backend.helper.encrypt import decode_string

logger = logging.getLogger(__name__)
router = APIRouter()

CHUNK_SIZE = 1024 * 1024  # 1MB


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

    end = min(end, file_size - 1)
    content_length = end - start + 1

    # Align to CHUNK_SIZE boundary
    offset = (start // CHUNK_SIZE) * CHUNK_SIZE
    first_part_cut = start - offset
    last_part_cut = (offset + math.ceil(content_length / CHUNK_SIZE) * CHUNK_SIZE) - end - 1
    part_count = math.ceil((content_length + first_part_cut) / CHUNK_SIZE)

    headers = {
        "Content-Type": mime_type,
        "Content-Length": str(content_length),
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
    }

    async def file_generator():
        part_index = 0
        async for chunk in bot.stream_media(message, offset=offset, limit=part_count):
            chunk_data = bytes(chunk)
            if part_index == 0:
                chunk_data = chunk_data[first_part_cut:]
            if part_index == part_count - 1:
                chunk_data = chunk_data[:len(chunk_data) - last_part_cut] if last_part_cut > 0 else chunk_data
            yield chunk_data
            part_index += 1

    status_code = 206 if range_header else 200
    return StreamingResponse(file_generator(), status_code=status_code, headers=headers)
