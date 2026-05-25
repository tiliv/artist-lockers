import logging
import re
import discord

logger = logging.getLogger(__name__)

BOT_MENTION_RE = re.compile(r'@bot\s+(.*)', re.IGNORECASE)


def parse_strategy(content: str) -> dict | None:
    """Extract @bot declaration from a thread starter message."""
    if not content:
        return None
    m = BOT_MENTION_RE.search(content)
    if not m:
        return None
    # TODO: parse album, lyrics-*, named parts
    return {"raw": m.group(1).strip()}


async def fetch_thread_strategy(thread: discord.Thread) -> dict | None:
    """Fetch thread starter and parse any @bot strategy declaration."""
    try:
        starter = await thread.parent.fetch_message(thread.id)
        return parse_strategy(starter.content)
    except discord.NotFound:
        return None


def register(client: discord.Client) -> None:

    @client.event
    async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent) -> None:
        channel = client.get_channel(payload.channel_id)
        if not isinstance(channel, discord.Thread):
            return
        if channel.id != payload.message_id:
            return  # not the thread starter
        content = (payload.data or {}).get("content", "")
        strategy = parse_strategy(content)
        if strategy:
            logger.info("Thread starter edited with strategy: %s", strategy)
            # TODO: trigger thread rescan with strategy

    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return
        if not isinstance(message.channel, discord.Thread):
            return
        # Only care if thread has a strategy — check discord cache first
        thread = message.channel
        starter = thread.starting_message  # None if not cached
        if starter is None:
            return  # let attachment trigger do the fetch
        strategy = parse_strategy(starter.content)
        if strategy is None:
            return
        # TODO: route message to ingestion with strategy context
