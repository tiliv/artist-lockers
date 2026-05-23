"""
Per-category bookmark files under _data/bookmarks/{category_id}.json.

Schema:
{
  "guild_id": "1234567890123456780"
  "category_id": "1234567890123456781",
  "category_name": "Music Locker",
  "last_sync": "2026-05-22T14:30:00Z",   # null if never synced
  "channels": {
    "987654321": null,                     # init'd, not yet scanned
    "111222333": "1234567890123456789"     # scanned to this message snowflake
  }
}

Merge strategy: existing keys are never deleted, cursors only advance.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import bootstrap
import discord

logger = logging.getLogger(__name__)

OUT_DIR = bootstrap.get_out()


def _bookmark_path(guild_id: int, category_id: int) -> Path:
    return OUT_DIR / f"{guild_id}/{category_id}/bookmarks.json"


def load(guild_id: int, category_id: int) -> Optional[dict]:
    """Load an existing bookmark file, or return None if it doesn't exist."""
    path = _bookmark_path(guild_id, category_id)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(guild_id: int, data: dict) -> Path:
    """Write a bookmark dict to disk, creating directories as needed."""
    path = _bookmark_path(guild_id, int(data["category_id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def make_stub(guild_id: int, category: discord.CategoryChannel) -> dict:
    """
    Build a fresh bookmark stub from a live category object.
    All top-level channels get a null cursor; threads are discovered lazily.
    """
    return {
        "guild_id": str(guild_id),
        "category_id": str(category.id),
        "category_name": category.name,
        "last_sync": None,
        "channels": {
            str(ch.id): None
            for ch in category.channels
            if isinstance(ch, (discord.TextChannel, discord.ForumChannel))
        },
    }


def merge_stub(existing: dict, category: discord.CategoryChannel) -> dict:
    """
    Merge a fresh stub into an existing bookmark.
    - Adds channels that are new since last init.
    - Never removes channels or resets cursors.
    - Updates category_name in case it was renamed.
    """
    existing["category_name"] = category.name
    channels = existing.setdefault("channels", {})
    for ch in category.channels:
        if isinstance(ch, (discord.TextChannel, discord.ForumChannel)):
            key = str(ch.id)
            if key not in channels:
                channels[key] = None
    return existing


def init_category(guild_id: int, category: discord.CategoryChannel) -> Path:
    """
    Create or update the bookmark stub for a category.
    Safe to run multiple times — only adds, never removes or resets.
    """
    existing = load(guild_id, category.id)
    if existing is None:
        data = make_stub(guild_id, category)
        logger.info("Created new bookmark stub for '%s'", category.name)
    else:
        data = merge_stub(existing, category)
        logger.info(
            "Merged bookmark stub for '%s' (%d channels)",
            category.name,
            len(data["channels"])
        )
    return save(guild_id, data)


def get_cursor(bookmark: dict, channel_id: int) -> Optional[int]:
    """Return the stored message_id for a channel, or None if unscanned."""
    raw = bookmark["channels"].get(str(channel_id))
    return int(raw) if raw is not None else None


def set_cursor(bookmark: dict, channel_id: int, message_id: int) -> None:
    """Advance a channel's cursor. Only moves forward, never back."""
    key = str(channel_id)
    current = bookmark["channels"].get(key)
    if current is None or message_id > int(current):
        bookmark["channels"][key] = str(message_id)


def touch_sync(bookmark: dict) -> None:
    """Update the last_sync timestamp to now."""
    bookmark["last_sync"] = datetime.now(timezone.utc).isoformat()
