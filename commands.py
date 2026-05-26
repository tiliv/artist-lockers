import argparse
import asyncio
import json
import logging
from pathlib import Path
import re
import sys
import time

import discord

import bookmarks
import bootstrap
import exporter
import decent
import refresh
import scanner


logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser(
    prog="cli.py",
    description="Discord media link scanner",
)
subparsers = parser.add_subparsers(dest="command", required=True)


async def run_sync(args, client: discord.Client) -> None:
    if args.init:
        return await run_sync_init(args, client)

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
                logger.info(
                    "Export written: %s (%d links)",
                    export_path, len(found_links)
                )
    finally:
        await client.close()


async def run_sync_init(args, client: discord.Client) -> None:
    try:
        pattern = re.compile(args.init)
    except re.error as e:
        logger.error("Invalid pattern '%s': %s", args.init, e)
        sys.exit(1)

    def match_categories(
        guild: discord.Guild, pattern: re.Pattern
    ) -> list[discord.CategoryChannel]:
        matched = [c for c in guild.categories if pattern.search(c.name)]
        if not matched:
            logger.warning(
                "No categories matching /%s/ in guild '%s'",
                pattern.pattern, guild.name
            )
        else:
            logger.info(
                "Matched %d categor%s in '%s': %s",
                len(matched),
                "y" if len(matched) == 1 else "ies",
                guild.name,
                [c.name for c in matched],
            )
        return matched

    await client.wait_until_ready()
    try:
        for guild in client.guilds:
            for category in match_categories(guild, pattern):
                path = bookmarks.init_category(guild.id, category)
                logger.info("Bookmark written: %s", path)
    finally:
        await client.close()


SYNC = "sync"
sync_parser = subparsers.add_parser(
    SYNC,
    help="Scan all tracked categories for media links"
)
sync_parser.add_argument(
    "--init",
    metavar="PATTERN",
    help="Create or update bookmark stubs for categories, no scanning",
)


async def run_refresh(args, client: discord.Client) -> None:
    await client.wait_until_ready()
    threshold_seconds = args.within * 3600
    output_dir = bootstrap.get_out()
    try:
        for guild in client.guilds:
            count = await refresh.refresh_guild(
                client, guild, threshold_seconds, output_dir
            )
            logger.info(
                "Guild '%s': %d attachment URL(s) refreshed", guild.name, count
            )
    finally:
        await client.close()


REFRESH = "refresh"
refresh_parser = subparsers.add_parser(
    REFRESH,
    help="Refresh expiring Discord CDN attachment URLs"
)
refresh_parser.add_argument(
    "--within",
    metavar="HOURS",
    type=float,
    default=24.0,
    help="Refresh URLs expiring within this many hours (default: 24)",
)


async def run_pin(args) -> None:
    deadline = time.monotonic() + args.budget
    total_pinned = 0

    for refs_path in decent.refs_paths():
        if time.monotonic() >= deadline:
            logger.info("Budget exhausted after %d pins", total_pinned)
            break

        with open(refs_path, encoding="utf-8") as f:
            payload = json.load(f)

        links = payload.get("links", [])
        dirty = False

        for entry in links:
            if time.monotonic() >= deadline:
                break
            if not decent.needs_pin(entry):
                continue

            url = entry["url"]
            filename = entry.get("attachment", {}).get("filename", "file")
            mime_type = entry.get("attachment", {}).get(
                "content_type", "application/octet-stream"
            )
            name = f"{entry['message']['id']}_{filename}"

            local_path = decent.fetch_to_temp(url)
            if not local_path:
                continue

            try:
                cid = decent.pin(local_path, mime_type, name)
                if cid:
                    entry["ipfs_cid"] = cid
                    total_pinned += 1
                    dirty = True
                    logger.info("Pinned %s -> %s", name, cid)
            finally:
                Path(local_path).unlink(missing_ok=True)

        if dirty:
            with open(refs_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            logger.info("Updated %s", refs_path)

    logger.info("Pin job complete: %d pinned", total_pinned)


PIN = "pin"
pin_parser = subparsers.add_parser(
    PIN, help="Upload unpinned attachments to IPFS")
pin_parser.add_argument(
    "--budget",
    metavar="SECONDS",
    type=float,
    default=300.0,
    help="Time budget for uploading in seconds (default: 300)",
)


commands = {
    SYNC: run_sync,
    REFRESH: run_refresh,
    PIN: run_pin,
}


def parse() -> None:
    args = parser.parse_args()

    try:
        token = bootstrap.get_token()
    except Exception:
        logger.error("DISCORD_BOT_TOKEN is not set. Use dotenv machinery.")
        raise

    cmd = commands[args.command]

    async def runner():
        async with client:
            await asyncio.gather(client.start(token), cmd(args, client))

    client = bootstrap.get_client()
    asyncio.run(runner())
