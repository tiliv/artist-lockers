## Dev

This is a template repository. That means you can use GitHub to copy it
directly to your account without forking this one. You will be detached from my
updates, which you should consider a feature! It's yours now. Make it cool.

### bin/bot.py
_Main entry point for logging in the bot._

### bin/cli.py
_Management entry point for causing backlogged message updates._

Briefly: We store a last-seen `message_id` per channel and forum post, and only
ask for updates on channels that have newer ids than ours.
