#!/usr/bin/env python
"""
CLI entry point for the Discord media bot.

Usage:
    uv run bot sync                           # scan all tracked categories
    uv run bot sync --init "Category Regex$"  # create/merge bookmark stubs
"""

import argparse
import asyncio
import logging
import re
import sys
from pathlib import Path

import discord

# flake8: noqa: E402
sys.path.insert(0, str(Path(__file__).parent.parent))

import bootstrap; bootstrap.load_env()
import bookmarks
import exporter
import refresh
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


async def run_sync(client: discord.Client) -> None:
    await client.wait_until_ready()
    try:
        for guild in client.guilds:
            found_links, bookmark_path = await scanner.sync_guild(guild)
            if bookmark_path:
                logger.info("Bookmarks flushed: %s", bookmark_path)
            if found_links:
                export_path = exporter.export_links(
                    guild.id,
                    found_links,
                    output_dir=bootstrap.get_out(),
                )
                logger.info("Export written: %s (%d links)", export_path, len(found_links))
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog=Path(__file__).name,
        description="Discord media link scanner",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Scan all tracked categories for media links")
    sync_parser.add_argument(
        "--init",
        metavar="PATTERN",
        help="Create or update bookmark stubs for categories matching regex, no scanning",
    )

    )

    args = parser.parse_args()

    try:
        token = bootstrap.get_token()
    except Exception:
        logger.error("DISCORD_BOT_TOKEN is not set. Use dotenv machinery.")
        raise

    if args.command == "sync" and args.init:
        try:
            pattern = re.compile(args.init)
        except re.error as e:
            logger.error("Invalid pattern '%s': %s", args.init, e)
            sys.exit(1)
        task = lambda c: run_init(c, pattern)
    elif args.command == "sync":
        task = run_sync

    async def runner():
        async with client:
            await asyncio.gather(client.start(token), task(client))

    client = bootstrap.get_client()
    asyncio.run(runner())


if __name__ == "__main__":
    main()
