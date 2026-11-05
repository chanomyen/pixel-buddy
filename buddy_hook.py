"""Fallback forwarder for `install_hooks.py --mode command`.

Reads the hook JSON from stdin and POSTs it to the Buddy server. Never fails and never
blocks Claude Code: any error is swallowed and the exit code is always 0.
"""
import os
import sys
import urllib.request


def main() -> None:
    try:
        data = sys.stdin.buffer.read()
        if not data:
            return
        port = int(os.environ.get("PIXEL_BUDDY_PORT", "7777"))
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/buddy-event", data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req, timeout=0.6).read()
    except Exception:
        pass


main()
