"""
Stores files somewhere decentralized. Sort of.
"""

import json
import logging
import os
import subprocess
import tempfile
import urllib.request
from pathlib import Path

import bootstrap

logger = logging.getLogger(__name__)


def refs_paths() -> list[Path]:
    return list(bootstrap.get_out().glob("*/*/refs.json"))


def needs_pin(entry: dict) -> bool:
    return (
        entry.get("source_type") == "attachment"
        and not entry.get("ipfs_cid")
        and entry.get("url")
    )


def fetch_to_temp(url: str) -> str | None:
    """Download a URL to a temp file, return path or None on failure."""
    try:
        suffix = Path(urllib.parse.urlparse(url).path).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            urllib.request.urlretrieve(url, f.name)
            return f.name
    except Exception as e:
        logger.error("Fetch failed for %s: %s", url, e)
        return None


def pin(local_path: str, mime_type: str, name: str) -> str | None:
    """Require synchronous push to IPFS."""
    result = subprocess.run(
        ["node", "bin/distribute.js", local_path, mime_type, name],
        capture_output=True,
        text=True,
        env=os.environ,
    )
    if result.returncode != 0:
        logger.error("Pin failed for %s: %s", name, result.stderr)
        return None
    return json.loads(result.stdout)["cid"]
