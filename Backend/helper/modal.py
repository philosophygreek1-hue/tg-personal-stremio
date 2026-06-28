"""
modal.py — Data models for Personal Video Stremio Addon

REUSED from original:  QualityDetail (Telegram file reference, same structure)
REPLACED:              MovieSchema, TVShowSchema, Episode, Season
NEW:                   VideoSchema, FolderSchema

The QualityDetail model is kept identical because the Telegram
streaming mechanism (encoded chat_id + message_id) is unchanged.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TelegramFile(BaseModel):
    """
    Represents a single video file stored in Telegram.
    REUSED from original QualityDetail — same fields, renamed for clarity.
    The 'id' field is a base64-encoded string of (chat_id, message_id)
    used by the streaming endpoint to fetch the file from Telegram.
    """
    id: str        # encoded chat_id + message_id
    name: str      # original filename
    size: str      # human readable e.g. "1.2 GB"


class VideoSchema(BaseModel):
    """
    Replaces MovieSchema. No TMDB/IMDB fields.
    A video has a user-chosen name, belongs to a folder, and
    stores the Telegram file reference.
    """
    title: str                          # user-chosen display name (editable)
    original_filename: str              # original filename from Telegram
    folder_id: Optional[str] = "root"  # which folder this belongs to
    telegram: Optional[TelegramFile] = None
    file_size: Optional[str] = None
    uploaded_on: datetime = Field(default_factory=datetime.utcnow)
    updated_on: datetime = Field(default_factory=datetime.utcnow)


class FolderSchema(BaseModel):
    """
    NEW — no equivalent in original project.
    Represents a folder/category for organizing videos.
    """
    name: str                           # display name (editable)
    created_on: datetime = Field(default_factory=datetime.utcnow)
    updated_on: datetime = Field(default_factory=datetime.utcnow)
