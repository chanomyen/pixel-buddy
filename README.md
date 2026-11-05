# 🐾 Pixel Buddy

แมวพิกเซลตัวเล็ก ๆ ที่วิ่งเล่นบน Task Bar ของ Windows 11 และสะท้อนว่า **Claude Code** กำลังทำอะไร ด้วยโมเดลอะไร

| สถานะ Claude Code | น้องแมวทำอะไร |
|---|---|
| ไม่มี session | นอนหลับ 💤 (ตัวเดียว) |
| ว่าง รอคำสั่ง | เดินเล่นช้า ๆ / นั่งกระพริบตา / หลับเมื่อว่างเกิน 60 วิ |
| กำลังคิด | เดินช้า มีจุด `...` ลอยเหนือหัว |
| `Read` `Grep` `Glob` | วิ่ง + ไอคอนแว่นขยาย |
| `Edit` `Write` | วิ่ง + ไอคอนดินสอ |
| `Bash` | วิ่งเร็ว + ไอคอนเทอร์มินัล |
| `WebSearch` `WebFetch` | วิ่ง + ไอคอนโลก |
| เครื่องมืออื่น / MCP | วิ่ง + ไอคอนเฟือง |
| Subagent ทำงาน | มีแมวจิ๋วตามหลังตัวละ 1 subagent (สูงสุด 4) |
| รอคุณอนุมัติ / ตอบ | กระโดด โบกมือ + เครื่องหมาย `?` |
| เสร็จ (Stop) | ตาหยี กระโดดดีใจ + ✓ |
| API error (StopFailure) | ตา X + `!` |

**โมเดลดูจากสี:** Sonnet = ส้ม · Haiku = เขียวมิ้นต์ (ตัวเล็กกว่า) · Opus = ม่วง + มงกุฎ · Fable/Mythos = ทอง + มงกุฎ
เอาเมาส์ชี้ (หรือคลิก) ที่ตัวแมวเพื่อดู tooltip: โปรเจกต์ · ชื่อโมเดล · งานที่ทำ · เวลาที่ใช้ไป
หลาย session พร้อมกัน = หลายตัว (1 session / ตัว) คลิกขวาที่ตัวแมวหรือไอคอนใน system tray เพื่อเปิดเมนู

## ติดตั้ง

### แบบโปรแกรม (แนะนำ — ไม่ต้องมี Python)

รัน `PixelBuddy-Setup.exe` (ติดตั้งแบบ per-user ไม่ต้องใช้สิทธิ์ admin) ตอนติดตั้งเลือกได้ว่าจะ
- ☑ เปิดอัตโนมัติเมื่อเริ่ม Windows
- ☑ ติดตั้ง hooks ใน Claude Code (สำรอง `~/.claude/settings.json` เดิมให้)

ถอนการติดตั้งจาก Settings → Apps จะลบ autostart และถอน hooks ให้ด้วย
สร้างตัวติดตั้งเอง: `powershell -ExecutionPolicy Bypass -File packaging\build.ps1` (ต้องมี [Inno Setup 6](https://jrsoftware.org/isinfo.php) สำหรับขั้นสุดท้าย; ถ้าไม่มีจะได้แค่ `dist\PixelBuddy\PixelBuddy.exe`)

### เมนูที่ system tray (คลิกขวาไอคอน หรือคลิกขวาที่ตัวน้อง)

| เมนู | ทำอะไร |
|---|---|
| รายการ session | ดูสถานะแต่ละ session |
| น้อง (สกิน) | เลือกตัวละคร: **แมว**, **กระต่าย** (มีให้) หรือสกินที่คุณทำเอง |
| นำเข้าสกิน… / เปิดโฟลเดอร์สกิน | เพิ่มสกินของตัวเอง (ดูด้านล่าง) |
| เปิดตอนเริ่ม Windows | เปิด/ปิด autostart (เขียน `HKCU\...\Run` ไม่ต้องใช้ admin) |
| Claude Code hooks | ติดตั้ง / อัปเดต / ถอน hooks (แจ้งถ้าพอร์ตไม่ตรง) |
| ออก | ปิดโปรแกรม |

การตั้งค่าเก็บที่ `%APPDATA%\PixelBuddy\config.json` (`skin`, `port`) สกินของผู้ใช้อยู่ที่ `%APPDATA%\PixelBuddy\skins\`

### ทำสกินของตัวเอง

ง่ายสุด: วาดรูป PNG พื้นหลังโปร่งใส 1 ไฟล์ (สูงไม่เกิน 90 px กว้างไม่เกิน 256 px) แล้วเลือก **นำเข้าสกิน…** รูปเดียวจะใช้ทุกท่า (กระโดด/เด้งตามสถานะให้เอง)

อยากให้ขยับ: ทำ **sprite sheet** — 1 แถว = 1 ท่า, 1 คอลัมน์ = 1 เฟรม (ช่องว่างเปล่าท้ายแถวจะถูกข้าม) ลำดับแถวเริ่มต้น `sit, walk, run, sleep, alert, happy, error` (ท่าที่ไม่มีจะใช้ท่าใกล้เคียง; ต้องมี `sit` อย่างน้อย) แล้วใส่ `skin.json` คู่กัน (นำเข้าเป็น `.zip` ที่มี `sheet.png` + `skin.json` หรือเลือก `skin.json` ได้):

```json
{
  "name": "น้องหมา",
  "frame_w": 24, "frame_h": 20,
  "scale": 3,
  "poses": ["sit", "walk", "run", "sleep", "alert", "happy", "error"],
  "chest": [4, 10, 14, 6]
}
```

`name`, `scale`, `poses`, `chest` (กรอบพิมพ์ตัวอักษรย่อโปรเจกต์ที่หน้าอก `[x, y, กว้าง, สูง]` หน่วยพิกเซลของรูปต้นฉบับ — ไม่ใส่ = ไม่แสดง) ไม่บังคับ ถ้าไม่ใส่ `frame_w/frame_h` จะถือว่าทั้งรูปคือ 1 เฟรม
สกินของผู้ใช้ **ไม่เปลี่ยนสีตามโมเดล** (สีตามโมเดลมีเฉพาะสกินที่มีให้)

### แบบรันจากซอร์ส (นักพัฒนา)

ต้องมี Python 3.10+ บน Windows

```powershell
cd pixel-buddy
pip install -r requirements.txt
python install_hooks.py          # หรือกดจากเมนู tray; สำรองไฟล์เดิมให้อัตโนมัติ
python -m pixel_buddy           # หรือดับเบิลคลิก buddy.pyw (ไม่มีหน้าต่าง console)
```

จากนั้นเปิด Claude Code session ใหม่ แล้วพิมพ์ `/hooks` เพื่อตรวจว่ามี hook ของ Buddy อยู่

ลองก่อนโดยไม่ต้องใช้ Claude Code: `python simulate.py --model claude-opus-4-1 --loop`
(เปิดเทอร์มินัลที่สองรันซ้ำด้วย `--sid b --model claude-haiku-4-5` เพื่อดูหลายตัว)

ถอนการติดตั้ง hooks: `python install_hooks.py --uninstall`

## ทำงานยังไง

```
Claude Code ──hook (HTTP POST)──▶ 127.0.0.1:7777 ──▶ core.py (state ต่อ session) ──▶ app.py วาดบน Task Bar
```

- `install_hooks.py` ลงทะเบียน hook แบบ `http` ให้ 13 event (SessionStart/End, UserPromptSubmit, Pre/PostToolUse, PostToolUseFailure, PermissionRequest, Notification, SubagentStart/Stop, Stop, StopFailure, PostModelSwitch) ถ้าโปรแกรมไม่ได้เปิดอยู่ hook จะล้มเหลวแบบ non-blocking ไม่กระทบ Claude Code
- Claude Code เวอร์ชันเก่าที่ยังไม่มี HTTP hook: `python install_hooks.py --mode command` (ใช้ `buddy_hook.py` ส่งต่อ event)
- **ชื่อโมเดล**: อ่านจาก `model` ใน SessionStart / PostModelSwitch และจากท้ายไฟล์ transcript (`transcript_path`) ตอน SessionStart, UserPromptSubmit, Stop — เปลี่ยนโมเดลด้วย `/model` กลาง session จะอัปเดตเอง
- หน้าต่างโปร่งใสไม่มีขอบ always-on-top วางให้ขาแมวแตะขอบบนของ Task Bar (`availableGeometry`) พิกเซลโปร่งใสคลิกทะลุไปยังแอปด้านล่าง
- ซ่อนอัตโนมัติเมื่อมีแอปเต็มจอ/เกม/นำเสนอ (`SHQueryUserNotificationState`) และดึง z-order กลับมาบนสุดทุกวินาทีเพราะ Windows 11 ชอบดัน Taskbar ขึ้นทับ

## ปรับแต่ง

| อยากทำ | แก้ที่ |
|---|---|
| วาดแมว/กระต่าย/เปลี่ยนสี/เพิ่มไอคอน | `pixel_buddy/sprites.py` (กริด 16×12 ตัวอักษร, `python preview_sprites.py` ดูตัวอย่าง) |
| ความเร็ว ขนาด ความสูงหน้าต่าง | ค่าคงที่ต้น `pixel_buddy/app.py` (`SPEED`, `WIN_H`, `FEET_SINK`) และ `BuiltinSkin.scale()` ใน `skins.py` |
| ข้อความ tooltip | `Manager._view()` ใน `pixel_buddy/core.py` |
| เปลี่ยนพอร์ต | `port` ใน `config.json` หรือตัวแปรสภาพแวดล้อม `PIXEL_BUDDY_PORT` แล้วกด "ติดตั้ง / อัปเดต hooks" ในเมนู tray (หรือ `install_hooks.py --port ...`) |

## ข้อจำกัดที่ควรรู้

- ดูได้เฉพาะ **Claude Code** (CLI / IDE / Desktop ที่ใช้ Claude Code) — แอปแชท claude.ai ไม่มี hook ให้ดึงสถานะ
- ชื่อโมเดลใน session ที่เพิ่งเริ่มอาจว่างจนกว่าจะมี event ที่อ่าน transcript ได้ (แสดง "ไม่ทราบโมเดล" เป็นสีเทา)
- รองรับ Task Bar ด้านล่างจอหลักเป็นหลัก (Task Bar ที่ซ่อนอัตโนมัติ: แมวจะยืนที่ขอบล่างของจอ)
- ถ้าองค์กรตั้ง `allowedHttpHookUrls` ต้องเพิ่ม `http://127.0.0.1:7777/*` หรือใช้ `--mode command`
- เซิร์ฟเวอร์ฟังเฉพาะ `127.0.0.1` และเก็บเฉพาะ metadata (ชื่อ tool, โมเดล, โฟลเดอร์) ไม่เก็บเนื้อหาบทสนทนา; โปรเซสอื่นในเครื่องส่ง event ปลอมมาได้ (ผลแค่แมวทำท่าแปลก ๆ)
- ตำแหน่ง/ลำดับชั้นหน้าต่างบน Taskbar ยังไม่ได้ยืนยันด้วยสายตาบน Windows 11 จริง อาจต้องจูนเล็กน้อย (`FEET_SINK`, `WIN_H`)
