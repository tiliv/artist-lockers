# Artist Lockers

This is a template repository. That means you can use GitHub to copy it
directly to your account without forking this one. You will be detached from my
updates, which you should consider a feature! It's yours now. Make it cool.

This repository is configured variously by:
- `.env`: Holds environment variables and sensitive secrets for dotenv loader
- `bin/setup`: Prepares static site tooling
- `bin/init`: Discovers channels for the bot to read

This repository contains multiple entry points:
- `bin/Locker`: Reads channels in categories
- `bin/daily "CategorySubstring"`: Reads channels in matching categories
- `bin/serve`: Runs the Jekyll dev server for inspection

This repository automatically builds and deploys for pushes to branch `main`.

## About

This is a bespoke Jekyll site that reads data committed by a discord.py bot.

The bot only needs to turn on long enough to read messages since it's last appearance.

Messages are only processed if they have a media signal: attachments, embeds, or links to supported music domains.

Media-focused information is stored per Category group in a server.

Messages and media are treated as stable once fetched.

## Engineering philosophy

Minimalism
: Code demonstrates clear signals of intent, without superficial comments
: Express variables and routines with full but strategically short names
: Prefer flatter structures to deeply nested ones
: Reduce outbound queries with aggressive long-lived File or Blob caching

Self-sufficiency
: All monolith entry points are offered by `bin/` executables
: Accumulate offline media caches
: No frameworks
: No third-party vendor support loaded by the frontend runtime
: Leverage modern standards in HTML, CSS, and JS

## Tooling

Python
: Managed by `uv`
: Versioned by `.python-version`
: Secrets provided via dotenv

Ruby
: Managed by `bundler`
: Versioned by `.ruby-version`

Node
: Managed by `npm`

CI/CD
: Performed by GitHub Actions
: Secrets provided via repository Secrets and Variables

Deployment
: Hosted on GitHub Pages

Discord API
: Provided to the bot by discord.py
: Provided to the static site users by the Discord-authenticated HTTP API

Static site
: Built by Jekyll
: Served by GitHub Pages, and Cloudflare in front of it

IPFS
: Provided over HTTP gateway via "Pinata" (sic)

## Terms

Server
: a Discord "Guild"
Locker
: a Discord "Category" of more channels
Channel
: a Discord text-type channel, or a forum_post-type thread
Author
: a Discord user account who posts inside channels within a Locker
