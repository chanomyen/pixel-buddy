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
หลาย session พร้อมกัน = หลายตัว (1 session / ตัว) คลิกขวาที่ตัวแมวหรือไอคอนใน system tray เพื่อดูรายการ/ออกจากโปรแกรม

## ติดตั้ง

ต้องมี Python 3.10+ บน Windows

```powershell
cd pixel-buddy
pip install -r requirements.txt
python install_hooks.py          # เพิ่ม hooks ลง ~/.claude/settings.json (สำรองไฟล์เดิมให้อัตโนมัติ)
python -m pixel_buddy           # หรือดับเบิลคลิก buddy.pyw (ไม่มีหน้าต่าง console)
```

จากนั้นเปิด Claude Code session ใหม่ แล้วพิมพ์ `/hooks` เพื่อตรวจว่ามี hook ของ Buddy อยู่

ลองก่อนโดยไม่ต้องใช้ Claude Code: `python simulate.py --model claude-opus-4-1 --loop`
(เปิดเทอร์มินัลที่สองรันซ้ำด้วย `--sid b --model claude-haiku-4-5` เพื่อดูหลายตัว)

ถอนการติดตั้ง: `python install_hooks.py --uninstall`

เริ่มพร้อม Windows: กด `Win+R` → `shell:startup` → วาง shortcut ของ `buddy.pyw`

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
| วาดแมว/เปลี่ยนสี/เพิ่มไอคอน | `pixel_buddy/sprites.py` (กริด 16×12 ตัวอักษร, `python preview_sprites.py` ดูตัวอย่าง) |
| ความเร็ว ขนาด ความสูงหน้าต่าง | ค่าคงที่ต้น `pixel_buddy/app.py` (`SPEED`, `SCALE`, `WIN_H`, `FEET_SINK`) |
| ข้อความ tooltip | `Manager._view()` ใน `pixel_buddy/core.py` |
| เปลี่ยนพอร์ต | ตัวแปรสภาพแวดล้อม `PIXEL_BUDDY_PORT` (และรัน `install_hooks.py --port ...`) |

## ข้อจำกัดที่ควรรู้

- ดูได้เฉพาะ **Claude Code** (CLI / IDE / Desktop ที่ใช้ Claude Code) — แอปแชท claude.ai ไม่มี hook ให้ดึงสถานะ
- ชื่อโมเดลใน session ที่เพิ่งเริ่มอาจว่างจนกว่าจะมี event ที่อ่าน transcript ได้ (แสดง "ไม่ทราบโมเดล" เป็นสีเทา)
- รองรับ Task Bar ด้านล่างจอหลักเป็นหลัก (Task Bar ที่ซ่อนอัตโนมัติ: แมวจะยืนที่ขอบล่างของจอ)
- ถ้าองค์กรตั้ง `allowedHttpHookUrls` ต้องเพิ่ม `http://127.0.0.1:7777/*` หรือใช้ `--mode command`
- เซิร์ฟเวอร์ฟังเฉพาะ `127.0.0.1` และเก็บเฉพาะ metadata (ชื่อ tool, โมเดล, โฟลเดอร์) ไม่เก็บเนื้อหาบทสนทนา; โปรเซสอื่นในเครื่องส่ง event ปลอมมาได้ (ผลแค่แมวทำท่าแปลก ๆ)
- ผมทดสอบ logic, การวาด และตัวติดตั้งแบบ headless บน Linux แล้ว แต่ **ยังไม่ได้รันบน Windows 11 จริง** ตำแหน่ง/ลำดับชั้นหน้าต่างบน Taskbar อาจต้องจูนเล็กน้อย (`FEET_SINK`, `WIN_H`)
