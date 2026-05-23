import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from models import FoundLink

logger = logging.getLogger(__name__)


def export_links(
    guild_id: str,
    category_id: str,
    links: list[FoundLink],
    output_dir: str | Path = ".",
) -> Path:
    """
    Export a list of FoundLink objects to a timestamped JSON file.
    Returns the path to the written file.
    """
    output_path = Path(output_dir) / f"{guild_id}/{category_id}/refs.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat() + "Z",
        "total_links": len(links),
        "links": [link.to_dict() for link in links],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    logger.info("Exported %d links to %s", len(links), output_path)
    return output_path
