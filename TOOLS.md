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
- QQ 相关问题先分清：是 OpenClaw 的 `qqbot` 插件，还是工作区里独立运行的 `qq-bot-3371871293`（NapCat + NoneBot）。两套链路完全不同，别混着查。
- 给用户发 WebUI 地址前，先确认是内网 IP 还是公网 IP，并亲测可达；用户在 Telegram/手机侧通常打不开内网地址。
- 没有真正把二维码图片/文件投递到当前通道前，不要说“已经发了”。先确认发送能力，再承诺。

---

Add whatever helps you do your job. This is your cheat sheet.
