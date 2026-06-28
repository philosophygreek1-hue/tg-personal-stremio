import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from Backend.config import Telegram
from Backend import db

logger = logging.getLogger(__name__)
router = APIRouter()

BASE_URL = Telegram.BASE_URL
ADDON_NAME = "My Videos"
ADDON_VERSION = "1.0.0"
PAGE_SIZE = 20


def _video_to_meta(video: dict) -> dict:
    return {
        "id": f"personalvideo:{video['_id']}",
        "type": "movie",
        "name": video.get("title", "Untitled"),
        "description": f"📁 {video.get('original_filename', '')}\n💾 {video.get('file_size', '')}",
        "poster": None,
        "posterShape": "square",
    }


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Content-Type": "application/json",
    }


@router.get("/{token}/manifest.json")
async def get_manifest(token: str):
    folders = await db.get_all_folders()
    catalogs = [
        {
            "id": "all_videos",
            "type": "movie",
            "name": "📹 All Videos",
            "extra": [{"name": "search", "isRequired": False}]
        }
    ]
    for folder in folders:
        catalogs.append({
            "id": f"folder:{folder['_id']}",
            "type": "movie",
            "name": f"📁 {folder['name']}",
            "extra": [{"name": "search", "isRequired": False}]
        })
    manifest = {
        "id": "com.personal.tgvideos",
        "version": ADDON_VERSION,
        "name": ADDON_NAME,
        "description": "Stream your personal videos from Telegram.",
        "types": ["movie"],
        "catalogs": catalogs,
        "resources": ["catalog", "meta", "stream"],
        "idPrefixes": ["personalvideo:"],
    }
    return JSONResponse(content=manifest, headers=_cors_headers())


@router.get("/{token}/catalog/movie/{catalog_id}.json")
@router.get("/{token}/catalog/movie/{catalog_id}/{extra}.json")
async def get_catalog(token: str, catalog_id: str, extra: str = ""):
    skip = 0
    search_query = None
    if extra:
        for part in extra.split("&"):
            if part.startswith("skip="):
                try:
                    skip = int(part.split("=")[1])
                except Exception:
                    pass
            elif part.startswith("search="):
                search_query = part.split("=", 1)[1]
    if search_query:
        videos = await db.search_videos(search_query, limit=PAGE_SIZE)
    elif catalog_id == "all_videos":
        videos = await db.get_all_videos(skip=skip, limit=PAGE_SIZE)
    elif catalog_id.startswith("folder:"):
        folder_id = catalog_id.replace("folder:", "")
        videos = await db.get_folder_videos(folder_id, skip=skip, limit=PAGE_SIZE)
    else:
        videos = []
    metas = [_video_to_meta(v) for v in videos]
    return JSONResponse(content={"metas": metas}, headers=_cors_headers())


@router.get("/{token}/meta/movie/{item_id}.json")
async def get_meta(token: str, item_id: str):
    video_id = item_id.replace("personalvideo:", "")
    video = await db.get_video(video_id)
    if not video:
        return JSONResponse(content={"meta": {}}, headers=_cors_headers())
    meta = _video_to_meta(video)
    return JSONResponse(content={"meta": meta}, headers=_cors_headers())


@router.get("/{token}/stream/movie/{item_id}.json")
async def get_stream(token: str, item_id: str):
    video_id = item_id.replace("personalvideo:", "")
    video = await db.get_video(video_id)
    if not video or not video.get("telegram"):
        return JSONResponse(content={"streams": []}, headers=_cors_headers())
    tg = video["telegram"]
    encoded_id = tg.get("id", "")
    stream_url = f"{BASE_URL}/dl/{encoded_id}/video.mkv"
    streams = [
        {
            "name": f"📹 {ADDON_NAME}",
            "title": f"📁 {video.get('original_filename', '')}\n💾 {tg.get('size', '')}",
            "url": stream_url,
        }
    ]
    return JSONResponse(content={"streams": streams}, headers=_cors_headers())
