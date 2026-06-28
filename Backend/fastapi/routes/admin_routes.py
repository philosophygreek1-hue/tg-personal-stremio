"""
admin_routes.py — Admin panel routes for Personal Video Library.

REUSED from original:
  - Basic auth pattern (ADMIN_USERNAME / ADMIN_PASSWORD)
  - FastAPI router structure
  - Jinja2 template rendering
  - Same URL patterns for admin panel

REPLACED:
  - Movie/series CRUD endpoints → Video/Folder CRUD endpoints
  - Rescan/Re-match → Rename video
  - Genre/quality filters → Folder assignment
"""

import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from Backend.config import Telegram
from Backend import db

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBasic()
templates = Jinja2Templates(directory="Backend/fastapi/templates")


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Basic auth — same pattern as original project."""
    correct_username = secrets.compare_digest(credentials.username, Telegram.ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, Telegram.ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ─── Admin Panel Pages ────────────────────────────────────────────────────────

@router.get("/admin", response_class=HTMLResponse)
async def admin_home(request: Request, _=Depends(verify_admin)):
    folders = await db.get_all_folders()
    total_videos = await db.count_videos()
    return templates.TemplateResponse("admin/home.html", {
        "request": request,
        "folders": folders,
        "total_videos": total_videos,
    })


@router.get("/media/manage", response_class=HTMLResponse)
async def media_manage(request: Request, folder_id: str = "all", _=Depends(verify_admin)):
    folders = await db.get_all_folders()
    if folder_id == "all":
        videos = await db.get_all_videos(limit=200)
    else:
        videos = await db.get_folder_videos(folder_id, limit=200)
    return templates.TemplateResponse("admin/media.html", {
        "request": request,
        "videos": videos,
        "folders": folders,
        "current_folder": folder_id,
    })


# ─── Folder API ───────────────────────────────────────────────────────────────

@router.post("/api/folders/create")
async def api_create_folder(request: Request, _=Depends(verify_admin)):
    data = await request.json()
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Folder name required")
    folder_id = await db.create_folder(name)
    return JSONResponse({"success": True, "folder_id": folder_id})


@router.post("/api/folders/{folder_id}/rename")
async def api_rename_folder(folder_id: str, request: Request, _=Depends(verify_admin)):
    data = await request.json()
    new_name = data.get("name", "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Name required")
    success = await db.rename_folder(folder_id, new_name)
    return JSONResponse({"success": success})


@router.delete("/api/folders/{folder_id}")
async def api_delete_folder(folder_id: str, _=Depends(verify_admin)):
    """Delete folder — videos are moved to root, not deleted."""
    success = await db.delete_folder(folder_id)
    return JSONResponse({"success": success})


@router.get("/api/folders")
async def api_get_folders(_=Depends(verify_admin)):
    folders = await db.get_all_folders()
    return JSONResponse({"folders": folders})


# ─── Video API ────────────────────────────────────────────────────────────────

@router.post("/api/videos/{video_id}/rename")
async def api_rename_video(video_id: str, request: Request, _=Depends(verify_admin)):
    data = await request.json()
    new_title = data.get("title", "").strip()
    if not new_title:
        raise HTTPException(status_code=400, detail="Title required")
    success = await db.rename_video(video_id, new_title)
    return JSONResponse({"success": success})


@router.post("/api/videos/{video_id}/move")
async def api_move_video(video_id: str, request: Request, _=Depends(verify_admin)):
    data = await request.json()
    folder_id = data.get("folder_id", "root")
    success = await db.move_video(video_id, folder_id)
    return JSONResponse({"success": success})


@router.delete("/api/videos/{video_id}")
async def api_delete_video(video_id: str, _=Depends(verify_admin)):
    """Delete video from database only. Telegram file stays."""
    deleted = await db.delete_video(video_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Video not found")
    return JSONResponse({"success": True})


@router.get("/api/videos")
async def api_get_videos(folder_id: str = "all", _=Depends(verify_admin)):
    if folder_id == "all":
        videos = await db.get_all_videos(limit=500)
    else:
        videos = await db.get_folder_videos(folder_id, limit=500)
    return JSONResponse({"videos": videos})
