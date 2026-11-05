"""Fake a Claude Code session so you can watch the critters without running Claude.

    python simulate.py                     # one Sonnet session, one pass
    python simulate.py --model claude-opus-4-1 --loop
    python simulate.py --sid b --model claude-haiku-4-5 --cwd C:/work/other   # run in a 2nd terminal
"""
import argparse
import json
import time
import urllib.request


def send(port, payload):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/buddy-event", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=2).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--sid", default="demo")
    ap.add_argument("--model", default="claude-sonnet-4-5")
    ap.add_argument("--cwd", default="C:/projects/demo-app")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--error", action="store_true", help="end the turn with an API error")
    a = ap.parse_args()

    base = {"session_id": a.sid, "cwd": a.cwd}

    def ev(name, wait=2.0, **kw):
        print("→", name, kw.get("tool_name", kw.get("notification_type", "")))
        send(a.port, {**base, "hook_event_name": name, **kw})
        time.sleep(wait)

    def tool(name, inp, wait=2.5):
        ev("PreToolUse", wait, tool_name=name, tool_input=inp)
        ev("PostToolUse", 0.6, tool_name=name)

    while True:
        ev("SessionStart", 3, model=a.model)
        ev("UserPromptSubmit", 3, prompt="demo")
        tool("Read", {"file_path": "src/app.py"})
        tool("Grep", {"pattern": "TODO"})
        tool("Edit", {"file_path": "src/app.py"})
        tool("WebSearch", {"query": "pyside6 transparent window"})
        ev("SubagentStart", 0.3)
        ev("SubagentStart", 0.3)
        tool("Bash", {"command": "pytest -q"}, 4)
        ev("SubagentStop", 0.3)
        ev("SubagentStop", 0.3)
        ev("PreToolUse", 0.1, tool_name="Bash", tool_input={"command": "rm -rf build"})
        ev("PermissionRequest", 0.1, tool_name="Bash")
        ev("Notification", 4, notification_type="permission_prompt", message="Claude needs your permission to use Bash")
        ev("PostToolUse", 1.5, tool_name="Bash")
        ev("StopFailure" if a.error else "Stop", 8)
        if not a.loop:
            break
    ev("SessionEnd", 0)


if __name__ == "__main__":
    main()
