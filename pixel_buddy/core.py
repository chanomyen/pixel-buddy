"""State tracking: turns Claude Code hook events into per-session state.

No Qt in here, so it can be tested anywhere.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_PORT = 7777

TOOL_KINDS = {
    "Read": "search", "Grep": "search", "Glob": "search", "LS": "search", "NotebookRead": "search",
    "Edit": "edit", "MultiEdit": "edit", "Write": "edit", "NotebookEdit": "edit",
    "Bash": "bash", "PowerShell": "bash", "BashOutput": "bash", "KillShell": "bash",
    "WebSearch": "web", "WebFetch": "web",
    "Task": "agent", "Agent": "agent",
}
FAMILIES = ("opus", "sonnet", "haiku", "fable", "mythos")
ALERT_NOTIFICATIONS = {"permission_prompt", "elicitation_dialog", "elicitation_url_dialog", "agent_needs_input"}


def tool_kind(name: str) -> str:
    return TOOL_KINDS.get(name, "tool")


def tool_detail(inp) -> str:
    if not isinstance(inp, dict):
        return ""
    for key in ("command", "file_path", "path", "pattern", "query", "url", "description", "prompt"):
        v = inp.get(key)
        if isinstance(v, str) and v:
            if key in ("file_path", "path"):
                v = os.path.basename(v.replace("\\", "/"))
            v = " ".join(v.split())
            return v[:48] + ("…" if len(v) > 48 else "")
    return ""


def parse_model(model: str | None) -> tuple[str, str]:
    """'claude-opus-4-1-20250805' -> ('Opus 4.1', 'opus')."""
    m = re.sub(r"\[.*?\]", "", (model or "").lower())
    if not m:
        return "", "unknown"
    fam = next((f for f in FAMILIES if f in m), "")
    if not fam:
        return model or "", f"other:{m}"  # unknown model name -> random (stable per name) colour
    nums = [p for p in re.split(r"[-_.:@/\s]", m) if p.isdigit() and len(p) <= 2]
    return f"{fam.capitalize()} {'.'.join(nums[:2])}".strip(), fam


def read_model(path: str, tail_bytes: int = 262144) -> str:
    """Latest assistant model id found in the tail of a Claude Code transcript (.jsonl)."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - tail_bytes))
            data = f.read()
    except OSError:
        return ""
    for line in reversed(data.splitlines()):
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        msg = obj.get("message")
        m = (msg.get("model") if isinstance(msg, dict) else None) or obj.get("model")
        if isinstance(m, str) and m and not m.startswith("<"):
            return m
    return ""


@dataclass
class Session:
    sid: str
    cwd: str = ""
    model: str = ""
    state: str = "idle"   # idle | thinking | tool | alert | done | error
    kind: str = ""
    tool: str = ""
    detail: str = ""
    message: str = ""
    since: float = field(default_factory=time.time)
    last_event: float = field(default_factory=time.time)
    turn_started: float = 0.0
    agents: int = 0


@dataclass
class View:
    sid: str
    project: str
    state: str    # sleep | idle | thinking | tool | alert | done | error
    kind: str
    family: str
    model: str
    agents: int
    text: str


def _fmt(sec: float) -> str:
    sec = int(max(0, sec))
    return f"{sec // 60}:{sec % 60:02d}" if sec >= 60 else f"{sec}s"


class Manager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, Session] = {}

    # ---- event intake -------------------------------------------------
    def handle(self, p: dict) -> None:
        ev = p.get("hook_event_name") or p.get("event") or ""
        sid = str(p.get("session_id") or "default")
        now = time.time()
        refresh = None
        with self._lock:
            if ev == "SessionEnd":
                self._sessions.pop(sid, None)
                return
            s = self._sessions.get(sid)
            if s is None:
                s = self._sessions[sid] = Session(sid=sid)
            s.last_event = now
            if isinstance(p.get("cwd"), str) and p["cwd"]:
                s.cwd = p["cwd"]
            m = p.get("model") or p.get("to_model")
            if isinstance(m, dict):
                m = m.get("id") or m.get("display_name")
            if isinstance(m, str) and m:
                s.model = m

            if ev == "SessionStart":
                self._set(s, "idle")
            elif ev == "UserPromptSubmit":
                s.turn_started, s.agents = now, 0
                self._set(s, "thinking")
            elif ev == "PreToolUse":
                name = str(p.get("tool_name") or "")
                s.tool, s.kind = name, tool_kind(name)
                s.detail = tool_detail(p.get("tool_input"))
                if not s.turn_started:
                    s.turn_started = now
                self._set(s, "tool")
            elif ev in ("PostToolUse", "PostToolUseFailure"):
                if s.state in ("tool", "alert"):
                    self._set(s, "thinking")
            elif ev in ("PermissionRequest",):
                s.message = "Permission requested for tool " + str(p.get("tool_name") or "")
                self._set(s, "alert")
            elif ev == "Notification":
                if p.get("notification_type") in ALERT_NOTIFICATIONS:
                    s.message = str(p.get("message") or "")
                    self._set(s, "alert")
            elif ev == "SubagentStart":
                s.agents += 1
            elif ev == "SubagentStop":
                s.agents = max(0, s.agents - 1)
            elif ev == "Stop":
                s.agents, s.turn_started = 0, 0.0
                self._set(s, "done")
            elif ev == "StopFailure":
                s.agents, s.turn_started = 0, 0.0
                self._set(s, "error")

            if ev in ("SessionStart", "UserPromptSubmit", "Stop") and isinstance(p.get("transcript_path"), str):
                refresh = p["transcript_path"]
        if refresh:
            threading.Thread(target=self._refresh_model, args=(sid, refresh), daemon=True).start()

    @staticmethod
    def _set(s: Session, state: str) -> None:
        if s.state != state:
            s.state, s.since = state, time.time()

    def _refresh_model(self, sid: str, path: str) -> None:
        m = read_model(path)
        if m:
            with self._lock:
                s = self._sessions.get(sid)
                if s:
                    s.model = m

    # ---- output for the UI --------------------------------------------
    def views(self, now: float | None = None) -> list[View]:
        now = now or time.time()
        out: list[View] = []
        with self._lock:
            for sid in list(self._sessions):
                s = self._sessions[sid]
                quiet = now - s.last_event
                if (s.state in ("idle", "done") and quiet > 1800) or quiet > 7200:
                    del self._sessions[sid]
                    continue
                out.append(self._view(s, now))
        return out

    def _view(self, s: Session, now: float) -> View:
        st = s.state
        idle_for = now - s.since
        if st == "done":
            if idle_for > 5:
                st, idle_for = "idle", idle_for - 5
        elif st == "error" and idle_for > 6:
            st, idle_for = "idle", idle_for - 6
        if st == "idle" and idle_for > 60:
            st = "sleep"
        label, family = parse_model(s.model)
        proj = os.path.basename(s.cwd.replace("\\", "/").rstrip("/")) or s.sid[:6]
        elapsed = f" · {_fmt(now - s.turn_started)}" if s.turn_started and st in ("thinking", "tool", "alert") else ""
        if st == "tool":
            what = f"Using {s.tool}" + (f": {s.detail}" if s.detail else "")
        else:
            what = {
                "sleep": "Sleeping 💤", "idle": "Idle, waiting for input", "thinking": "Thinking…",
                "alert": "Waiting for your answer/approval!" + (f" ({s.message})" if s.message else ""),
                "done": "Done ✅", "error": "Error (API) ❌",
            }[st]
        sub = f" · subagent ×{s.agents}" if s.agents else ""
        text = f"{proj} · {label or 'unknown model'}\n{what}{elapsed}{sub}"
        return View(s.sid, proj, st, s.kind, family, label, s.agents, text)


# ---- HTTP server ---------------------------------------------------------
def start_server(mgr: Manager, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            try:
                n = min(int(self.headers.get("Content-Length") or 0), 2_000_000)
                mgr.handle(json.loads(self.rfile.read(n) or b"{}"))
            except Exception:
                pass
            self.send_response(204)
            self.end_headers()

        def do_GET(self):  # noqa: N802
            body = json.dumps([v.__dict__ for v in mgr.views()], ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):  # silence
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)  # localhost only
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
