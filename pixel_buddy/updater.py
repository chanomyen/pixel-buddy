"""Update check against the latest GitHub release. No Qt in here.

Only looks up the newest release; never downloads or installs anything. The user opens the release page.
"""
from __future__ import annotations

import json
import re
import urllib.request

from . import __version__

REPO = "chanomyen/pixel-buddy"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases/latest"
TIMEOUT = 8


def parse_version(s: str) -> tuple[int, ...] | None:
    """'v1.2.3' / '1.2.3-dev' -> (1, 2, 3). None if not parseable."""
    m = re.match(r"^\s*v?(\d+(?:\.\d+)*)", s or "")
    return tuple(int(p) for p in m.group(1).split(".")) if m else None


def is_newer(latest: str, current: str = __version__) -> bool:
    a, b = parse_version(latest), parse_version(current)
    if a is None or b is None:
        return False
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) > b + (0,) * (n - len(b))


def fetch_latest() -> tuple[str, str] | None:
    """Return (version, page_url) of the newest release, or None on any failure (offline, rate limit, ...)."""
    req = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"PixelBuddy/{__version__}",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8"))
        tag = str(data.get("tag_name") or "")
        if parse_version(tag) is None or data.get("draft") or data.get("prerelease"):
            return None
        url = str(data.get("html_url") or RELEASES_URL)
        if not url.startswith(f"https://github.com/{REPO}/"):
            url = RELEASES_URL
        return tag.lstrip("v"), url
    except (OSError, ValueError, AttributeError):
        return None
