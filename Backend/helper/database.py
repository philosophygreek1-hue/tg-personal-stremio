"""
database.py — MongoDB operations for Personal Video Stremio Addon

REUSED from original:
  - Motor async MongoDB connection pattern
  - ObjectId conversion helper
  - Database class structure

REPLACED:
  - MovieSchema/TVShowSchema CRUD → VideoSchema/FolderSchema CRUD
  - sort_movies, sort_tv_shows, search_documents → get_videos, get_folder_videos, search_videos
  - Multi-database sharding removed (single DB for personal use)
"""

import logging
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from Backend.config import Telegram
from Backend.helper.modal import VideoSchema, FolderSchema

logger = logging.getLogger(__name__)


def _serialize(doc: dict) -> dict:
    """Convert ObjectId to string — same helper as original project."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


class Database:
    def __init__(self):
        if not Telegram.DATABASE:
            raise ValueError("DATABASE environment variable is required.")
        self.client = AsyncIOMotorClient(Telegram.DATABASE)
        db_name = "personal_videos"
        self.db = self.client[db_name]
        self.videos = self.db["videos"]
        self.folders = self.db["folders"]
        logger.info(f"Database connected: {db_name}")

    # ─── Folder Operations ───────────────────────────────────────────────

    async def create_folder(self, name: str) -> str:
        """Create a new folder. Returns the new folder's _id as string."""
        folder = FolderSchema(name=name)
        result = await self.folders.insert_one(folder.model_dump())
        return str(result.inserted_id)

    async def get_all_folders(self) -> list[dict]:
        """Return all folders sorted by name."""
        cursor = self.folders.find().sort("name", 1)
        return [_serialize(doc) async for doc in cursor]

    async def get_folder(self, folder_id: str) -> dict | None:
        """Get a single folder by ID."""
        try:
            doc = await self.folders.find_one({"_id": ObjectId(folder_id)})
            return _serialize(doc) if doc else None
        except Exception:
            return None

    async def rename_folder(self, folder_id: str, new_name: str) -> bool:
        """Rename a folder."""
        result = await self.folders.update_one(
            {"_id": ObjectId(folder_id)},
            {"$set": {"name": new_name, "updated_on": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def delete_folder(self, folder_id: str) -> bool:
        """
        Delete a folder and move all its videos to root.
        Does NOT delete the actual Telegram files.
        """
        await self.videos.update_many(
            {"folder_id": folder_id},
            {"$set": {"folder_id": "root", "updated_on": datetime.utcnow()}}
        )
        result = await self.folders.delete_one({"_id": ObjectId(folder_id)})
        return result.deleted_count > 0

    # ─── Video Operations ────────────────────────────────────────────────

    async def add_video(self, title: str, original_filename: str,
                        encoded_id: str, file_size: str,
                        folder_id: str = "root") -> str:
        """
        Save a new video after it's uploaded to Telegram.
        Called by the file_receiver plugin when a new file arrives.
        """
        from Backend.helper.modal import TelegramFile
        video = VideoSchema(
            title=title,
            original_filename=original_filename,
            folder_id=folder_id,
            file_size=file_size,
            telegram=TelegramFile(
                id=encoded_id,
                name=original_filename,
                size=file_size,
            )
        )
        result = await self.videos.insert_one(video.model_dump())
        logger.info(f"Video saved: {title} ({file_size})")
        return str(result.inserted_id)

    async def get_all_videos(self, skip: int = 0, limit: int = 100) -> list[dict]:
        """Get all videos across all folders, newest first."""
        cursor = self.videos.find().sort("uploaded_on", -1).skip(skip).limit(limit)
        return [_serialize(doc) async for doc in cursor]

    async def get_folder_videos(self, folder_id: str, skip: int = 0, limit: int = 100) -> list[dict]:
        """Get videos in a specific folder."""
        cursor = self.videos.find({"folder_id": folder_id}).sort("uploaded_on", -1).skip(skip).limit(limit)
        return [_serialize(doc) async for doc in cursor]

    async def get_video(self, video_id: str) -> dict | None:
        """Get a single video by its MongoDB ID."""
        try:
            doc = await self.videos.find_one({"_id": ObjectId(video_id)})
            return _serialize(doc) if doc else None
        except Exception:
            return None

    async def rename_video(self, video_id: str, new_title: str) -> bool:
        """Rename a video (display title only, Telegram file unchanged)."""
        result = await self.videos.update_one(
            {"_id": ObjectId(video_id)},
            {"$set": {"title": new_title, "updated_on": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def move_video(self, video_id: str, folder_id: str) -> bool:
        """Move a video to a different folder."""
        result = await self.videos.update_one(
            {"_id": ObjectId(video_id)},
            {"$set": {"folder_id": folder_id, "updated_on": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def delete_video(self, video_id: str) -> dict | None:
        """
        Delete a video from the database.
        Returns the deleted doc so caller can delete from Telegram too.
        """
        doc = await self.videos.find_one_and_delete({"_id": ObjectId(video_id)})
        return _serialize(doc) if doc else None

    async def search_videos(self, query: str, limit: int = 50) -> list[dict]:
        """Search videos by title (case-insensitive)."""
        cursor = self.videos.find(
            {"title": {"$regex": query, "$options": "i"}}
        ).sort("uploaded_on", -1).limit(limit)
        return [_serialize(doc) async for doc in cursor]

    async def count_videos(self, folder_id: str | None = None) -> int:
        """Count videos, optionally filtered by folder."""
        query = {"folder_id": folder_id} if folder_id else {}
        return await self.videos.count_documents(query)
