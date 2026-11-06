# 🐾 Pixel Buddy

Tiny pixel cats that roam your Windows 11 taskbar and mirror what **Claude Code** is doing, and with which model.

| Claude Code state | What the cat does |
|---|---|
| No session | Sleeps 💤 (single cat) |
| Idle, waiting for input | Strolls slowly / sits and blinks / falls asleep after 60 s idle |
| Thinking | Walks slowly, `...` floats above its head |
| `Read` `Grep` `Glob` | Runs + magnifier icon |
| `Edit` `Write` | Runs + pencil icon |
| `Bash` | Runs fast + terminal icon |
| `WebSearch` `WebFetch` | Runs + globe icon |
| Other tools / MCP | Runs + gear icon |
| Subagent running | One mini cat follows behind per subagent (max 4) |
| Waiting for your approval / answer | Jumps, waves + `?` mark |
| Done (Stop) | Squinting eyes, happy jump + ✓ |
| API error (StopFailure) | X eyes + `!` |

**Model is shown by colour:** Sonnet = orange · Haiku = mint green (smaller) · Opus = purple + crown · Fable/Mythos = gold + crown
Hover (or click) a cat to see a tooltip: project · model name · current task · elapsed time.
Multiple sessions at once = multiple cats (1 session per cat). Right-click a cat or the system tray icon for the menu.

## Install

### As a program (recommended — no Python needed)

Run `PixelBuddy-Setup.exe` (per-user install, no admin rights needed). During setup you can choose to:
- ☑ Run automatically at Windows startup
- ☑ Install hooks in Claude Code (your existing `~/.claude/settings.json` is backed up)

Uninstalling from Settings → Apps removes the autostart entry and the hooks too.
Build the installer yourself: `powershell -ExecutionPolicy Bypass -File packaging\build.ps1` ([Inno Setup 6](https://jrsoftware.org/isinfo.php) is required for the final step; without it you only get `dist\PixelBuddy\PixelBuddy.exe`)

### System tray menu (right-click the icon, or right-click a buddy)

| Menu item | What it does |
|---|---|
| Session list | Shows the status of each session |
| Buddy (skin) | Pick a character: **Cat**, **Bunny** (built in) or your own skin |
| Import skin… / Open skins folder | Add your own skin (see below) |
| Run at Windows startup | Toggle autostart (writes `HKCU\...\Run`, no admin needed) |
| Check for updates automatically / now | Looks up the latest GitHub release (at start, then at most once a day). Shows a toast and a menu entry that opens the download page; nothing is installed automatically. Set `check_updates` to `false` in `config.json` to disable |
| Claude Code hooks | Install / update / remove hooks (warns if the port doesn't match) |
| Quit | Exit the program |

Settings are stored in `%APPDATA%\PixelBuddy\config.json` (`skin`, `port`). User skins live in `%APPDATA%\PixelBuddy\skins\`.

### Make your own skin

Easiest: draw a single transparent-background PNG (at most 90 px tall and 256 px wide) and choose **Import skin…**. The one image is used for every pose (jumping/bobbing by state is applied automatically).

Want animation: make a **sprite sheet** — 1 row = 1 pose, 1 column = 1 frame (empty cells at the end of a row are skipped). Default row order is `sit, walk, run, sleep, alert, happy, error` (missing poses fall back to a similar one; `sit` is required). Add a `skin.json` alongside (import as a `.zip` containing `sheet.png` + `skin.json`, or pick `skin.json` directly):

```json
{
  "name": "Doggo",
  "frame_w": 24, "frame_h": 20,
  "scale": 3,
  "poses": ["sit", "walk", "run", "sleep", "alert", "happy", "error"],
  "chest": [4, 10, 14, 6]
}
```

`name`, `scale`, `poses` and `chest` are optional (`chest` is the box where the project initial is drawn on the chest, `[x, y, width, height]` in source-image pixels — omit it to hide the initial). Without `frame_w/frame_h` the whole image is treated as a single frame.
User skins **do not change colour by model** (model colours apply only to the built-in skins).

### Run from source (developers)

Requires Python 3.10+ on Windows.

```powershell
cd pixel-buddy
pip install -r requirements.txt
python install_hooks.py          # or use the tray menu; backs up your existing file automatically
python -m pixel_buddy           # or double-click buddy.pyw (no console window)
```

Then start a new Claude Code session and type `/hooks` to check that the Buddy hooks are present.

Try it without Claude Code: `python simulate.py --model claude-opus-4-1 --loop`
(run it again in a second terminal with `--sid b --model claude-haiku-4-5` to see multiple cats)

Uninstall hooks: `python install_hooks.py --uninstall`

## How it works

```
Claude Code ──hook (HTTP POST)──▶ 127.0.0.1:7777 ──▶ core.py (per-session state) ──▶ app.py paints on the taskbar
```

- `install_hooks.py` registers `http` hooks for 13 events (SessionStart/End, UserPromptSubmit, Pre/PostToolUse, PostToolUseFailure, PermissionRequest, Notification, SubagentStart/Stop, Stop, StopFailure, PostModelSwitch). If the program isn't running, the hook fails non-blocking and Claude Code is unaffected.
- Older Claude Code versions without HTTP hooks: `python install_hooks.py --mode command` (uses `buddy_hook.py` to forward events)
- **Model name**: read from `model` in SessionStart / PostModelSwitch and from the tail of the transcript file (`transcript_path`) on SessionStart, UserPromptSubmit, Stop — switching models with `/model` mid-session updates automatically.
- A frameless, transparent, always-on-top window is placed so the cats' feet touch the top edge of the taskbar (`availableGeometry`). Transparent pixels are click-through to the apps beneath.
- Hides automatically when a fullscreen app/game/presentation is active (`SHQueryUserNotificationState`) and re-raises its z-order every second because Windows 11 likes to push the taskbar above it.

## Customising

| To change | Edit |
|---|---|
| Draw the cat/bunny, change colours, add icons | `pixel_buddy/sprites.py` (16×12 character grids; `python preview_sprites.py` for a preview) |
| Speed, size, window height | Constants at the top of `pixel_buddy/app.py` (`SPEED`, `WIN_H`, `FEET_SINK`) and `BuiltinSkin.scale()` in `skins.py` |
| Tooltip text | `Manager._view()` in `pixel_buddy/core.py` |
| Change the port | `port` in `config.json` or the `PIXEL_BUDDY_PORT` environment variable, then choose "Install / update hooks" in the tray menu (or `install_hooks.py --port ...`) |

## Known limitations

- Only **Claude Code** is observable (CLI / IDE / Desktop using Claude Code) — the claude.ai chat app has no hooks to read state from
- The model name in a freshly started session may be empty until an event that can read the transcript arrives (shown as a grey "unknown model")
- Mainly supports a taskbar at the bottom of the primary display (auto-hidden taskbar: the cats stand at the bottom edge of the screen)
- If your organisation sets `allowedHttpHookUrls`, add `http://127.0.0.1:7777/*` or use `--mode command`
- The server listens on `127.0.0.1` only and stores only metadata (tool names, model, folder), never conversation content; other local processes can send fake events (the only effect is odd cat behaviour)
- Window position/z-order on the taskbar has not been verified visually on a real Windows 11 machine and may need slight tuning (`FEET_SINK`, `WIN_H`)
