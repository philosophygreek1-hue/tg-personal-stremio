import logging
import math
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from Backend.helper.encrypt import decode_string

logger = logging.getLogger(__name__)
router = APIRouter()

CHUNK_SIZE = 1024 * 1024


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
        logger.error(f"Could not fetch message: {e}")
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
            parts = range_header.replace("bytes=", "").split("-")
            start = int(parts[0])
            end = int(parts[1]) if parts[1] else file_size - 1
        except Exception:
            pass

    end = min(end, file_size - 1)
    content_length = end - start + 1

    headers = {
        "Content-Type": mime_type,
        "Content-Length": str(content_length),
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
    }

    if request.method == "HEAD":
        from fastapi.responses import Response
        return Response(headers=headers)

    async def generator():
        remaining = content_length
        current_pos = start

        async for chunk in bot.stream_media(message, offset=start, limit=math.ceil(content_length / CHUNK_SIZE)):
            if remaining <= 0:
                break
            chunk_data = bytes(chunk)
            if len(chunk_data) > remaining:
                chunk_data = chunk_data[:remaining]
            remaining -= len(chunk_data)
            current_pos += len(chunk_data)
            yield chunk_data

    return StreamingResponse(
        generator(),
        status_code=206 if range_header else 200,
        headers=headers
    )
