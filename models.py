from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FoundLink:
    """A media link found in a Discord message, with full context for deep-linking."""

    # The link itself
    url: str
    platform: str  # "suno" | "udio"

    # Message context
    message_id: int
    message_content: str
    message_timestamp: datetime
    author_id: int
    author_name: str

    # Channel context
    channel_id: int
    channel_name: str
    channel_type: str  # "text" | "forum_post" | "thread"

    # Parent context (forum channel or category)
    parent_channel_id: Optional[int] = None
    parent_channel_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None

    # Guild
    guild_id: int = 0
    guild_name: str = ""

    @property
    def deep_link(self) -> str:
        """Discord web deep link to the exact message."""
        return f"https://discord.com/channels/{self.guild_id}/{self.channel_id}/{self.message_id}"

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "platform": self.platform,
            "deep_link": self.deep_link,
            "message": {
                "id": str(self.message_id),
                "content": self.message_content,
                "timestamp": self.message_timestamp.isoformat(),
                "author_id": str(self.author_id),
                "author_name": self.author_name,
            },
            "channel": {
                "id": str(self.channel_id),
                "name": self.channel_name,
                "type": self.channel_type,
            },
            "parent_channel": {
                "id": str(self.parent_channel_id) if self.parent_channel_id else None,
                "name": self.parent_channel_name,
            },
            "category": {
                "id": str(self.category_id) if self.category_id else None,
                "name": self.category_name,
            },
            "guild": {
                "id": str(self.guild_id),
                "name": self.guild_name,
            },
        }
