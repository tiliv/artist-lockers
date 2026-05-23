import re
import logging
from typing import AsyncIterator, Optional

import discord

from models import FoundLink

logger = logging.getLogger(__name__)

DOMAINS = ["suno", "udio", "youtube", "soundcloud", "spotify"]
DOMAIN_RE = r"https?://(?:\w+\.)?(?:{0})\.\w+/\S+"  # umm

# flake8: noqa: E731
_re_domain = lambda s: re.compile(DOMAIN_RE.format(s), re.IGNORECASE)
COMBINED_PATTERN = _re_domain('|'.join(DOMAINS))
PLATFORM_PATTERNS: dict[str, re.Pattern] = {
    name: _re_domain(name)
    for name in DOMAINS
}


def _detect_platform(url: str) -> Optional[str]:
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.match(url):
            return platform
    return None


def _extract_urls(text: str) -> list[str]:
    return COMBINED_PATTERN.findall(text)


def _channel_type_label(channel: discord.abc.GuildChannel | discord.Thread) -> str:
    if isinstance(channel, discord.Thread):
        return "forum_post" if isinstance(channel.parent, discord.ForumChannel) else "thread"
    if isinstance(channel, discord.ForumChannel):
        return "forum"
    return "text"


def _build_found_link(
    url: str,
    message: discord.Message,
    channel: discord.abc.GuildChannel | discord.Thread,
    parent: Optional[discord.abc.GuildChannel] = None,
) -> Optional[FoundLink]:
    platform = _detect_platform(url)
    if not platform:
        return None

    guild = message.guild
    category = getattr(channel, "category", None) or (
        getattr(parent, "category", None) if parent else None
    )

    return FoundLink(
        url=url,
        platform=platform,
        message_id=message.id,
        message_content=message.content,
        message_timestamp=message.created_at,
        author_id=message.author.id,
        author_name=str(message.author),
        channel_id=channel.id,
        channel_name=channel.name,
        channel_type=_channel_type_label(channel),
        parent_channel_id=parent.id if parent else None,
        parent_channel_name=parent.name if parent else None,
        category_id=category.id if category else None,
        category_name=category.name if category else None,
        guild_id=guild.id if guild else 0,
        guild_name=guild.name if guild else "",
    )


def _has_new_messages(
    channel: discord.abc.GuildChannel | discord.Thread,
    cursor: Optional[int],
) -> bool:
    """
    Cheap pre-filter using Discord's cached last_message_id.
    If cursor is None (never scanned), always proceed.
    If last_message_id is unavailable, assume there may be new content.
    """
    if cursor is None:
        return True
    last = getattr(channel, "last_message_id", None)
    if last is None:
        return True
    return last > cursor


async def scan_messages(
    channel: discord.abc.Messageable,
    source_channel: discord.abc.GuildChannel | discord.Thread,
    cursor: Optional[int] = None,
    parent: Optional[discord.abc.GuildChannel] = None,
) -> AsyncIterator[tuple[FoundLink, int]]:
    """
    Yield (FoundLink, message_id) tuples from messages after the cursor.
    Yields the message_id even for messages with no links, so the caller
    can advance the bookmark cursor to the true last-seen position.
    """
    after = discord.Object(id=cursor) if cursor is not None else None
    try:
        async for message in channel.history(
            limit=None, oldest_first=True, after=after
        ):
            # Always yield the message_id as a cursor advance signal
            if message.content:
                for url in _extract_urls(message.content):
                    link = _build_found_link(url, message, source_channel, parent)
                    if link:
                        yield link, message.id
                        break  # one yield per message is enough to advance cursor
                else:
                    # No links found but we still need to advance the cursor;
                    # yield None link with the message_id
                    yield None, message.id
            else:
                yield None, message.id
    except discord.Forbidden:
        logger.warning("No permission to read %s", getattr(source_channel, "name", source_channel))
    except discord.HTTPException as e:
        logger.error("HTTP error reading %s: %s", getattr(source_channel, "name", source_channel), e)


async def scan_text_channel(
    channel: discord.TextChannel,
    bookmark: dict,
    set_cursor_fn,
) -> AsyncIterator[FoundLink]:
    """Scan a text channel and its threads, respecting and advancing cursors."""
    channel_cursor = _get_cursor_from_bookmark(bookmark, channel.id)

    if _has_new_messages(channel, channel_cursor):
        async for link, msg_id in scan_messages(channel, channel, cursor=channel_cursor):
            set_cursor_fn(channel.id, msg_id)
            if link:
                yield link
    else:
        logger.debug("  Skipping #%s (no new messages)", channel.name)

    # Active threads
    try:
        for thread in channel.threads:
            async for link in _scan_thread(thread, parent=channel, bookmark=bookmark, set_cursor_fn=set_cursor_fn):
                yield link
    except discord.Forbidden:
        logger.warning("Cannot list threads in %s", channel.name)

    # Archived threads
    try:
        async for thread in channel.archived_threads(limit=None):
            async for link in _scan_thread(thread, parent=channel, bookmark=bookmark, set_cursor_fn=set_cursor_fn):
                yield link
    except discord.Forbidden:
        logger.warning("Cannot list archived threads in %s", channel.name)


async def scan_forum_channel(
    forum: discord.ForumChannel,
    bookmark: dict,
    set_cursor_fn,
) -> AsyncIterator[FoundLink]:
    """Scan all active and archived forum posts, respecting and advancing cursors."""
    try:
        for thread in forum.threads:
            async for link in _scan_thread(thread, parent=forum, bookmark=bookmark, set_cursor_fn=set_cursor_fn):
                yield link
    except discord.Forbidden:
        logger.warning("Cannot list posts in forum %s", forum.name)

    try:
        async for thread in forum.archived_threads(limit=None):
            async for link in _scan_thread(thread, parent=forum, bookmark=bookmark, set_cursor_fn=set_cursor_fn):
                yield link
    except discord.Forbidden:
        logger.warning("Cannot list archived posts in forum %s", forum.name)


async def _scan_thread(
    thread: discord.Thread,
    parent: discord.abc.GuildChannel,
    bookmark: dict,
    set_cursor_fn,
) -> AsyncIterator[FoundLink]:
    """Scan a single thread, lazily registering it in the bookmark if new."""
    thread_cursor = _get_cursor_from_bookmark(bookmark, thread.id)

    if not _has_new_messages(thread, thread_cursor):
        logger.debug("    Skipping thread '%s' (no new messages)", thread.name)
        return

    async for link, msg_id in scan_messages(thread, thread, cursor=thread_cursor, parent=parent):
        set_cursor_fn(thread.id, msg_id)
        if link:
            yield link


def _get_cursor_from_bookmark(bookmark: dict, channel_id: int) -> Optional[int]:
    raw = bookmark["channels"].get(str(channel_id))
    return int(raw) if raw is not None else None


async def scan_category(
    category: discord.CategoryChannel,
    bookmark: dict,
    set_cursor_fn,
) -> AsyncIterator[FoundLink]:
    """Scan all text and forum channels in a category using bookmark cursors."""
    logger.info("Scanning category: %s (%d channels)", category.name, len(category.channels))
    for channel in category.channels:
        if isinstance(channel, discord.TextChannel):
            logger.info("  Text channel: #%s", channel.name)
            async for link in scan_text_channel(channel, bookmark, set_cursor_fn):
                yield link
        elif isinstance(channel, discord.ForumChannel):
            logger.info("  Forum channel: #%s", channel.name)
            async for link in scan_forum_channel(channel, bookmark, set_cursor_fn):
                yield link
        else:
            logger.debug("  Skipping unsupported channel type: %s", type(channel).__name__)
