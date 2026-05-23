#!/usr/bin/env python
"""
CLI entry point for the Discord media bot.

Usage:
    uv run bot sync "Category Regex$"         # scan all matching categories, update bookmarks
    uv run bot sync "Category Regex$" --init  # create/merge bookmark stubs, no scanning
"""

import argparse
import asyncio
import logging
import os
import re
import sys
from pathlib import Path

import discord

# flake8: noqa: E402
sys.path.insert(0, str(Path(__file__).parent.parent))

import bootstrap; bootstrap.load_env()
import bookmarks
import exporter
import scanner

logger = logging.getLogger(__name__)


def match_categories(
    guild: discord.Guild, pattern: re.Pattern
) -> list[discord.CategoryChannel]:
    matched = [c for c in guild.categories if pattern.search(c.name)]
    if not matched:
        logger.warning("No categories matching /%s/ in guild '%s'", pattern.pattern, guild.name)
    else:
        logger.info(
            "Matched %d categor%s in '%s': %s",
            len(matched),
            "y" if len(matched) == 1 else "ies",
            guild.name,
            [c.name for c in matched],
        )
    return matched


async def run_init(client: discord.Client, pattern: re.Pattern) -> None:
    await client.wait_until_ready()
    try:
        for guild in client.guilds:
            for category in match_categories(guild, pattern):
                path = bookmarks.init_category(guild.id, category)
                logger.info("Bookmark written: %s", path)
    finally:
        await client.close()


async def run_sync(client: discord.Client, pattern: re.Pattern) -> None:
    await client.wait_until_ready()
    try:
        for guild in client.guilds:
            for category in match_categories(guild, pattern):
                bookmark = bookmarks.load(guild.id, category.id)
                if bookmark is None:
                    logger.error(
                        "No bookmark found for '%s' (id: %d). Run with --init first.",
                        category.name,
                        category.id,
                    )
                    continue

                found_links = []

                def set_cursor(channel_id: int, message_id: int) -> None:
                    bookmarks.set_cursor(bookmark, channel_id, message_id)
                    # Also register previously-unseen threads lazily
                    key = str(channel_id)
                    if key not in bookmark["channels"]:
                        bookmark["channels"][key] = None

                async for link in scanner.scan_category(category, bookmark, set_cursor):
                    found_links.append(link)
                    logger.debug(
                        "Found %s link in #%s: %s",
                        link.platform,
                        link.channel_name,
                        link.url,
                    )

                bookmarks.touch_sync(bookmark)
                path = bookmarks.save(guild.id, bookmark)
                logger.info(
                    "Bookmark updated: %s (%d links found this run)",
                    path,
                    len(found_links)
                )

                if found_links:
                    export_path = exporter.export_links(
                        guild.id,
                        category.id,
                        found_links,
                        output_dir=bootstrap.get_out()
                    )
                    logger.info("Export written: %s", export_path)
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog=Path(__file__).name,
        description="Discord media link scanner",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser(
        "sync",
        help="Scan categories for media links"
    )
    sync_parser.add_argument(
        "pattern",
        help="Regex pattern to match category names (e.g. 'Locker$')",
    )
    sync_parser.add_argument(
        "--init",
        action="store_true",
        help="Create or update bookmark stubs only, no scanning",
    )

    args = parser.parse_args()

    try:
        token = bootstrap.get_token()
    except Exception:
        logger.error("DISCORD_BOT_TOKEN is not set. Use dotenv machinery.")
        raise

    try:
        pattern = re.compile(args.pattern)
    except re.error as e:
        logger.error("Invalid pattern '%s': %s", args.pattern, e)
        sys.exit(1)

    client = bootstrap.make_client()
    task = run_init if args.init else run_sync

    async def runner():
        async with client:
            await asyncio.gather(
                client.start(token),
                task(client, pattern),
            )

    asyncio.run(runner())


if __name__ == "__main__":
    main()
