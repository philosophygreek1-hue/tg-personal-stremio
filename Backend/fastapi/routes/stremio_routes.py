"""
stremio_routes.py — Stremio Addon endpoints for Personal Video Library.

REUSED from original:
  - FastAPI router structure mounted at /stremio
  - Token-based URL pattern /stremio/{token}/...
  - Manifest endpoint pattern
  - Stream URL construction using BASE_URL + /dl/{id}/video.mkv
  - CORS headers pattern

REPLACED:
  - Movie/series catalog types → "other" type with per-folder catalogs
  - TMDB ID-based item IDs → MongoDB ObjectId-based IDs
  - convert_to_stremio_meta (TMDB fields) → convert_video_to_meta (title + folder)
  - Genre filtering → folder filtering
  - format_stream_details (PTN parser) → simple name + size display
"""

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
    """
    Convert a VideoSchema document to Stremio meta format.
    REPLACES convert_to_stremio_meta from original (which needed TMDB fields).
    Uses only our own fields: title, _id, file_size, uploaded_on.
    """
    return {
        "id": f"personalvideo:{video['_id']}",
        "type": "other",
        "name": video.get("title", "Untitled"),
        "description": f"📁 {video.get('original_filename', '')}\n💾 {video.get('file_size', '')}",
        "poster": None,
    }


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "*",
        "Content-Type": "application/json",
    }


@router.get("/{token}/manifest.json")
async def get_manifest(token: str):
    """
    Manifest endpoint — declares addon capabilities to Stremio.

    REUSED structure from original.
    REPLACED: movie/series types → other type with dynamic folder catalogs.

    Each folder becomes its own catalog so Stremio shows them separately.
    An "All Videos" catalog is always present.
    """
    folders = await db.get_all_folders()

    catalogs = [
        {
            "id": "all_videos",
            "type": "other",
            "name": "📹 All Videos",
            "extra": [{"name": "search", "isRequired": False}]
        }
    ]

    for folder in folders:
        catalogs.append({
            "id": f"folder:{folder['_id']}",
            "type": "other",
            "name": f"📁 {folder['name']}",
            "extra": [{"name": "search", "isRequired": False}]
        })

    manifest = {
        "id": "com.personal.tgvideos",
        "version": ADDON_VERSION,
        "name": ADDON_NAME,
        "description": "Stream your personal videos from Telegram.",
        "types": ["other"],
        "catalogs": catalogs,
        "resources": ["catalog", "meta", "stream"],
        "idPrefixes": ["personalvideo:"],
    }

    return JSONResponse(content=manifest, headers=_cors_headers())


@router.get("/{token}/catalog/other/{catalog_id}.json")
@router.get("/{token}/catalog/other/{catalog_id}/{extra}.json")
async def get_catalog(token: str, catalog_id: str, extra: str = ""):
    """
    Catalog endpoint — returns list of videos for a folder or all videos.

    REUSED: pagination pattern (skip-based) from original.
    REPLACED: sort_movies/sort_tv_shows → get_folder_videos/get_all_videos.
    """
    # Parse skip from extra path like "skip=20"
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


@router.get("/{token}/meta/other/{item_id}.json")
async def get_meta(token: str, item_id: str):
    """
    Meta endpoint — returns details for a single video.
    REUSED: response structure from original.
    REPLACED: TMDB fields → our VideoSchema fields.
    """
    video_id = item_id.replace("personalvideo:", "")
    video = await db.get_video(video_id)
    if not video:
        return JSONResponse(content={"meta": {}}, headers=_cors_headers())

    meta = _video_to_meta(video)
    meta["videos"] = [
        {
            "id": item_id,
            "title": video.get("title", "Play"),
            "released": str(video.get("uploaded_on", "")),
        }
    ]

    return JSONResponse(content={"meta": meta}, headers=_cors_headers())


@router.get("/{token}/stream/other/{item_id}.json")
async def get_stream(token: str, item_id: str):
    """
    Stream endpoint — returns playable stream URL for a video.

    REUSED from original:
      - Stream object format {name, title, url}
      - URL pattern: BASE_URL/dl/{encoded_id}/video.mkv

    REPLACED:
      - Quality sorting (PTN parser) → not needed, one file per video
      - TMDB title in stream name → our own title
    """
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
