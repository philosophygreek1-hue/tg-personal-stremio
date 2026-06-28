"""
encrypt.py — Telegram file ID encoding/decoding.
REUSED from original project without modification.
Encodes (chat_id, message_id) into a base64 string used in stream URLs.
"""

import base64


def encode_string(chat_id: int, message_id: int) -> str:
    raw = f"{chat_id}:{message_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_string(encoded: str) -> tuple[int, int]:
    raw = base64.urlsafe_b64decode(encoded.encode()).decode()
    chat_id, message_id = raw.split(":")
    return int(chat_id), int(message_id)
