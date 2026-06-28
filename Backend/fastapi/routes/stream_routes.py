import math
import asyncio
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, Response
from pyrogram import raw, utils
from pyrogram.errors import AuthBytesInvalid
from pyrogram.session import Session, Auth
from pyrogram.file_id import FileId, FileType, ThumbnailSource
from Backend.helper.encrypt import decode_string

logger = logging.getLogger(__name__)
router = APIRouter()

CHUNK_SIZE = 1024 * 1024  # 1MB


async def get_file_id(bot, chat_id: int, message_id: int) -> FileId:
    """Get FileId object from a Telegram message."""
    message = await bot.get_messages(chat_id, message_id)
    if not message or message.empty:
        raise FileNotFoundError("Message not found")
    
    media = message.video or message.document or message.audio
    if not media:
        raise FileNotFoundError("No media in message")

    media_obj = getattr(media, "file_id", None)
    if not media_obj:
        raise FileNotFoundError("No file_id")

    file_id = FileId.decode(media_obj)
    setattr(file_id, "file_size", media.file_size)
    setattr(file_id, "mime_type", getattr(media, "mime_type", "video/mp4"))
    setattr(file_id, "file_name", getattr(media, "file_name", "video.mp4"))
    return file_id


async def get_media_session(bot, file_id: FileId):
    """Get or create a media session for the file's DC."""
    dc_id = file_id.dc_id
    
    if dc_id in bot.media_sessions:
        return bot.media_sessions[dc_id]

    test_mode = await bot.storage.test_mode()
    current_dc = await bot.storage.dc_id()

    if dc_id == current_dc:
        session = bot.session
    else:
        auth_key = await Auth(bot, dc_id, test_mode).create()
        session = Session(bot, dc_id, auth_key, test_mode, is_media=True)
        await session.start()

        for attempt in range(6):
            try:
                exported = await bot.invoke(
                    raw.functions.auth.ExportAuthorization(dc_id=dc_id)
                )
                await session.send(
                    raw.functions.auth.ImportAuthorization(
                        id=exported.id, bytes=exported.bytes
                    )
                )
                break
            except AuthBytesInvalid:
                await asyncio.sleep(0.5)

        bot.media_sessions[dc_id] = session

    return session


def get_location(file_id: FileId):
    """Get Telegram file location from FileId."""
    file_type = file_id.file_type
    if file_type == FileType.PHOTO:
        return raw.types.InputPhotoFileLocation(
            id=file_id.media_id,
            access_hash=file_id.access_hash,
            file_reference=file_id.file_reference,
            thumb_size=file_id.thumbnail_size,
        )
    return raw.types.InputDocumentFileLocation(
        id=file_id.media_id,
        access_hash=file_id.access_hash,
        file_reference=file_id.file_reference,
        thumb_size=file_id.thumbnail_size,
    )


@router.get("/dl/{encoded_id}/video.mkv")
@router.head("/dl/{encoded_id}/video.mkv")
async def stream_video(encoded_id: str, request: Request):
    from Backend import bot

    try:
        chat_id, message_id = decode_string(encoded_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid stream ID")

    try:
        file_id = await get_file_id(bot, chat_id, message_id)
    except Exception as e:
        logger.error(f"Could not get file: {e}")
        raise HTTPException(status_code=404, detail="File not found")

    file_size = file_id.file_size
    mime_type = getattr(file_id, "mime_type", "video/mp4")

    range_header = request.headers.get("Range", "")
    if range_header:
        try:
            parts = range_header.replace("bytes=", "").split("-")
            start = int(parts[0])
            end = int(parts[1]) if parts[1] else file_size - 1
        except Exception:
            start, end = 0, file_size - 1
    else:
        start, end = 0, file_size - 1

    end = min(end, file_size - 1)
    content_length = end - start + 1

    # Align to chunk boundary
    offset = start - (start % CHUNK_SIZE)
    first_part_cut = start - offset
    last_part_cut = (end % CHUNK_SIZE) + 1
    part_count = math.ceil(end / CHUNK_SIZE) - math.floor(offset / CHUNK_SIZE)

    headers = {
        "Content-Type": mime_type,
        "Content-Length": str(content_length),
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Cache-Control": "public, max-age=3600",
    }

    if request.method == "HEAD":
        return Response(headers=headers, status_code=206 if range_header else 200)

    try:
        session = await get_media_session(bot, file_id)
        location = get_location(file_id)
    except Exception as e:
        logger.error(f"Session error: {e}")
        raise HTTPException(status_code=500, detail="Streaming session error")

    async def generator():
        for part_index in range(part_count):
            chunk_offset = offset + (part_index * CHUNK_SIZE)
            try:
                r = await asyncio.wait_for(
                    session.send(
                        raw.functions.upload.GetFile(
                            location=location,
                            offset=chunk_offset,
                            limit=CHUNK_SIZE,
                        )
                    ),
                    timeout=30,
                )
                chunk = getattr(r, "bytes", b"")
                if not chunk:
                    break

                # Trim first and last chunks
                if part_index == 0:
                    chunk = chunk[first_part_cut:]
                if part_index == part_count - 1:
                    chunk = chunk[:last_part_cut]

                yield chunk
            except Exception as e:
                logger.error(f"Chunk error at offset {chunk_offset}: {e}")
                break

    return StreamingResponse(
        generator(),
        status_code=206 if range_header
