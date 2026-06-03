# Artist Lockers

This is a template repository. That means you can use GitHub to copy it
directly to your account without forking this one. You will be detached from my
updates, which you should consider a feature! It's yours now. Make it cool.

This repository contains multiple entry points.

## ./bin

These files compose commands with increasingly high-level abstractions.

All main tasks are in shell scripts, which eventually call the `bot.py` or
`cli.py`.

Primary daily tasks are held in the executable `daily` script, but are in a
generic form requiring an argument for the regex for matching only valid Discord
"category" group names when pulling channels.

Excepting `init`, the category-matcher string argument is not required, but
`daily` includes repeat calls to `init` so that new channels are discovered.

To streamline the base case for a single known server, the esoteric script
`Locker` will call `daily` with "Locker" as the argument.

As such, the `Locker` script is runnable without arguments.

(WIP)

## discord.py bot

All bot code is Python and lives in ./bot. There are no entry points here, but
`commands.py` holds argument parsing for functions exposed by `bin/cli.py`.

The bot does not need to be running to passively monitor messages, but could at
some future date. `bot/watcher.py` was a stub no longer in use.

`./worker` is for if we ever have to switch off of a "public" discord oauth app,
so that it can mint tokens with a deployed secret. For now, we do not use this.

## IPFS distributor

`bin/pin` is a separate entry point that launches a CLI process to download
attachments that have been accumulated in each server's category's channel set
("_data/[guildid]/[categoryid]/refs.json"). Any raw attachment without an
"ipfs_cid" field is considered untracked.

Via `bin/distribute.mjs`, a file is uploaded to a free Pinata account using
their latest APIs. The script prints the new CID for that file, and writes it
back to the relevant `refs.json`.

## Jekyll static site

`bin/setup` sets up Ruby bundler and install. `bin/serve` starts the incremental
Jekyll dev server.

The static site fundamentally depends on the bot's `bin/daily` efforts,
specifically the json artifacts in `_data/`. Changes to those files must be
committed so that CI/CD in `.github/workflows/jekyll.yml` can build a site that
renders references to those baked artifacts.

This static result is deployed to GitHub Pages. It can be given a CNAME
