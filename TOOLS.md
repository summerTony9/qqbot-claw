# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

## Local Gotchas

- When using `exec` for live inspection during a chat, keep output minimal and user-relevant. On this setup, raw shell output may end up visible enough to annoy the user.
- If a quiet first-class tool path fails and shell fallback is necessary, summarize the result instead of pasting command output.
- For host admin commands in `exec`, `/usr/sbin` and `/sbin` may be missing from PATH. Use full paths (for example `/usr/sbin/useradd`) or export `PATH=/usr/sbin:/sbin:$PATH` first.

---

Add whatever helps you do your job. This is your cheat sheet.
